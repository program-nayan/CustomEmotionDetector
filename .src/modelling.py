import torch
import torch.nn as nn
import torch.nn.functional as F
from transformers import RobertaPreTrainedModel, RobertaModel

class MultiTaskRoberta(RobertaPreTrainedModel):
    def __init__(self, config):
        super().__init__(config)
        self.roberta = RobertaModel(config=config, add_pooling_layer=True)
        
        # Hyperparameters for Focal Loss
        self.gamma = getattr(config, "focal_gamma", 2.0)
        
        # Register smoothed weights as a buffer for GPU/CPU compatibility
        if hasattr(config, "emo_weights"):
            self.register_buffer("emo_weights", torch.tensor(config.emo_weights, dtype=torch.float32))
        else:
            self.emo_weights = None

        self.emo_dropout = nn.Dropout(0.2)
        self.emo_classifier = nn.Linear(config.hidden_size, 7)

        self.act_dropout = nn.Dropout(0.2)
        self.act_classifier = nn.Linear(config.hidden_size, 4)

        self.post_init()

    def forward(self, input_ids=None, attention_mask=None, label_emo=None, label_act=None):
        outputs = self.roberta(input_ids, attention_mask=attention_mask)
        pooled_output = outputs.pooler_output 
        
        emo_logits = self.emo_classifier(self.emo_dropout(pooled_output))
        act_logits = self.act_classifier(self.act_dropout(pooled_output))

        loss = None
        if label_emo is not None and label_act is not None:

            # 1. Get raw Cross Entropy (no weights) to calculate true probabilities
            raw_ce = F.cross_entropy(emo_logits, label_emo, reduction='none')
            pt = torch.exp(-raw_ce) # pt is the probability of the correct class
            
            # 2. Apply the Focal Term: (1 - pt)^gamma
            focal_term = (1 - pt) ** self.gamma
            
            # 3. Combine with weights and mean ensure each sample gets its class weight
            weights = self.emo_weights[label_emo]
            weighted_focal_loss = (focal_term * raw_ce * weights).sum() / weights.sum()

            #  ACT LOSS 
            act_loss = F.cross_entropy(act_logits, label_act)

            # Prioritize Emotion (0.7) as it's the harder task
            loss = (0.8 * weighted_focal_loss) + (0.2 * act_loss)
        return (loss, (emo_logits, act_logits)) if loss is not None else ((emo_logits, act_logits),)