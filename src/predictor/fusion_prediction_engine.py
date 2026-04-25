from src.predictor.roberta_predictions import RobertaEmotionPredictor
from src.predictor.gemini_predictions import GeminiEmotion

class FusionPredictor():
    def __init__(self):
      self.roberta_object = RobertaEmotionPredictor()
      self.gemini_object = GeminiEmotion()

    def fuse_scores(self, text, context=""):
        # get score dictionaries
        roberta_scores = self.roberta_object.predict(text, context)
        gemini_scores = self.gemini_object.get_result(text, context)

        # Get label of the predicted class and detect sarcasm
        predicted_roberta_label = max(roberta_scores['Emotion Scores'], key=roberta_scores['Emotion Scores'].get)
        is_sarcasm = gemini_scores['Is Sarcasm']

        final_act_scores = roberta_scores['Act Scores']

        # Shift weights to gemini model if predicition is neutral
        if predicted_roberta_label == 0:
            r_weight, g_weight = 0.2, 0.8
        # A little more weight to gemini for sarcasm 
        elif is_sarcasm:
            r_weight, g_weight = 0.4, 0.6
        # More weight to roberta model for general use cases
        else:
            r_weight, g_weight = 0.7, 0.3

        final_emo_scores = {
            rkey : (r_weight * rvalue + g_weight * gvalue)
            for (rkey, rvalue), (gkey, gvalue) in zip(
                roberta_scores['Emotion Scores'].items(),
                gemini_scores['Emotion Scores'].items()
                )
                }
        
        return final_emo_scores, final_act_scores

