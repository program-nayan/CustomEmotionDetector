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

            # Retrieve emotion weights securely from config to avoid initialization corruption via accelerate / fast_init
            secure_emo_weights = None
            if hasattr(self.config, "emo_weights") and self.config.emo_weights is not None:
                secure_emo_weights = torch.tensor(self.config.emo_weights, dtype=torch.float32, device=emo_logits.device)

            # Native PyTorch Cross Entropy is optimized and strictly normalizes weights.
            # Cast logits to fp32 to prevent FP16 autocast NaN overflows with fp32 weight tensors.
            emo_loss = F.cross_entropy(emo_logits.float(), label_emo, weight=secure_emo_weights)

            #  ACT LOSS 
            act_loss = F.cross_entropy(act_logits.float(), label_act)

            # Prioritize Emotion (0.8) as it's the harder task
            loss = (0.7 * emo_loss) + (0.3 * act_loss)
        return (loss, (emo_logits, act_logits)) if loss is not None else ((emo_logits, act_logits),)