from torch.optim import AdamW
import numpy as np
from sklearn.metrics import accuracy_score, f1_score
from transformers import TrainingArguments, Trainer, DataCollatorWithPadding

class CustomTrainer(Trainer):
    def create_optimizer(self):
        if self.optimizer is None:
            backbone_params = []
            custom_head_params = []
            for name, param in self.model.named_parameters():
                if not param.requires_grad:
                    continue
                # The pooler in RoBERTa is initialized randomly when loaded from `roberta-base`.
                # We move it to the custom head so it trains at a higher learning rate!
                if 'roberta' in name and 'pooler' not in name:
                    backbone_params.append(param)
                else:
                    custom_head_params.append(param)
            
            optimizer_grouped_parameters = [
                {"params": backbone_params, "lr": 2e-5},
                {"params": custom_head_params, "lr": 5e-4}
            ]
            self.optimizer = AdamW(optimizer_grouped_parameters, weight_decay=self.args.weight_decay, eps=self.args.adam_epsilon)
        return self.optimizer

class ModelTrainer():
    def __init__(self, model, epochs, tokenizer):
        self.model = model
        self.epochs = epochs
        self.tokenizer = tokenizer
        self.data_collator = DataCollatorWithPadding(self.tokenizer)
    
    def compute_metrics(self, eval_pred):
        logits, labels = eval_pred
        
        # Unpack multi-task outputs
        emo_logits, act_logits = logits
        label_emo, label_act = labels

        emo_preds = np.argmax(emo_logits, axis=-1)
        act_preds = np.argmax(act_logits, axis=-1)

        return {
            "emo_f1_macro": f1_score(label_emo, emo_preds, average='macro'),
            "emo_accuracy": accuracy_score(label_emo, emo_preds),
            "act_f1_macro": f1_score(label_act, act_preds, average='macro'),
            "act_accuracy": accuracy_score(label_act, act_preds),
        }
    
    def get_trainer(self, train_data, validation_data):
        # 1. Define Training Arguments
        training_args = TrainingArguments(
            num_train_epochs=self.epochs,
            output_dir="./custom_roberta_checkpoints",
            per_device_train_batch_size= 32,
            gradient_accumulation_steps=2,
            per_device_eval_batch_size = 64,
            
            eval_strategy='steps',
            eval_steps=500, 
            logging_steps=100, 
            save_strategy='steps',
            save_steps=500,

            weight_decay=0.01,
            warmup_steps=100,
            max_grad_norm=1.0,
            fp16=True,
            dataloader_num_workers=8,
            report_to=[],

            # main conditions for custom model
            lr_scheduler_type="cosine",
            label_names= ['label_emo', 'label_act'],
            load_best_model_at_end= True,
            metric_for_best_model='emo_f1_macro',
        )

        # 2. Instantiate the CustomTrainer
        trainer = CustomTrainer(
            model=self.model,
            args=training_args,
            data_collator=self.data_collator,
            train_dataset=train_data,
            eval_dataset=validation_data,
            compute_metrics=self.compute_metrics,
        )
        
        return trainer