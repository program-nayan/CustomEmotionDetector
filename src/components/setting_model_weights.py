import torch
import numpy as np
from transformers import AutoConfig

class CustomWeights():
    def __init__(self, df):
        self.df = df
        self.config = AutoConfig.from_pretrained('FacebookAI/roberta-base')

    def custom_weight_calculation(self):
    # Calculate counts for each class
        class_counts = self.df['Emotion Label'].value_counts().sort_index().values
        total_samples = len(self.df)

        # Square root smoothing formula: weight = sqrt(N_total / N_class)
        # Then normalized so the average weight is 1.0
        smoothed_weights = np.sqrt(total_samples / class_counts)
        normalized_weights = smoothed_weights / np.mean(smoothed_weights)
        emotion_weights_tensor = torch.tensor(normalized_weights, dtype=torch.float32)

        # We convert your tensor to a list so it can be saved as a standard JSON file later
        normalized_weights = emotion_weights_tensor / emotion_weights_tensor.sum() * len(emotion_weights_tensor)
        self.config.emo_weights = normalized_weights.tolist()

        return self.config
