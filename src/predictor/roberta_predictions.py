import torch
from torch import nn
from transformers import AutoTokenizer
from src.components.modelling import MultiTaskRoberta
import torch.nn.functional as F

class RobertaEmotionPredictor():
    def __init__(self, model_path = "./custom_roberta_multitask_final"):
        # get tokenizer and model
        self.tokenizer = AutoTokenizer.from_pretrained(model_path)
        self.model = MultiTaskRoberta.from_pretrained(model_path)

        self.device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
        self.model.to(self.device)
        
        # set model to evaluation mode
        self.model.eval()

        # define emotion and act labels map
        self.emo_map = {0: "neutral", 1: "anger", 2: "disgust", 3: "fear", 4: "happiness", 5: "sadness", 6: "surprise"}
        self.act_map = {0: "inform", 1: "question", 2: "directive", 3: "commissive"}

    def predict(self, text, context=""):

        # convert to tokens
        inputs = self.tokenizer(
            context,
            text,
            max_length = 350,
            truncation = True,
            padding = True,
            return_tensors = 'pt'
        ).to(self.device)

        # run inference
        with torch.inference_mode():
            # get outputs
            outputs = self.model(**inputs)

            # get raw logits
            emo_logits, act_logits = outputs[0]

            # get probabilities using softmax function
            emo_probs = F.softmax(input= emo_logits, dim=-1)
            act_probs = F.softmax(input= act_logits, dim=-1)

            # scores dict
            emo_score_dict = {}
            for i in range(7):
                emo_score_dict[i] = emo_probs[0][i].item()
            act_score_dict = {}
            for i in range(4):
                act_score_dict[i] = act_probs[0][i].item()

        return {
            "Emotion Scores" : emo_score_dict,
            "Act Scores" : act_score_dict
        }
    