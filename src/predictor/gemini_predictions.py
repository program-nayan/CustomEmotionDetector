import os
from dotenv import load_dotenv
from google import genai
import re
import ast

class GeminiEmotion():
    def __init__(self, model="models/gemma-3-27b-it"):
        load_dotenv()

        GEMINI_API = os.getenv("GEMINI_API_KEY")
        self.MODEL_NAME = "models/gemma-3-27b-it"
        self.client = genai.Client(api_key= GEMINI_API)

        self.emo_map = {0: "neutral", 1: "anger", 2: "disgust", 3: "fear", 4: "happiness", 5: "sadness", 6: "surprise"}
        self.act_map = {0: "inform", 1: "question", 2: "directive", 3: "commissive"}
        self.prompt = None

    def get_result(self, text, context=""):
        self.prompt = f''' 
        System : 
        You are an expert system designed to detect emotions and classify them into these seven different emotion classes : {self.emo_map} and these four different action categories {self.act_map}.
        You classify the sentences into these labels by using context and text pairs. You are expert at detecting emotion in sarcasm.
        Role : 
        Categorize the given text : "{text}" and the context "{context}" into given emotions : {self.emo_map} and actions : {self.act_map}.
        Constraints :
        1. STRICTLY RETURN A VALID JSON OBJECT NOTHING ELSE.
        2. Sarcasm value should be a boolean (true/false).
        3. Emotion and Act keys should be the integer labels (0-6 and 0-3).
        Task : 
        Return a JSON object with keys: "Is Sarcasm", "Emotion", "Act".
        Example Output:
        {{
            "Is Sarcasm": false,
            "Emotion": {{ "0": 0.1, "1": 0.05, "2": 0.05, "3": 0.05, "4": 0.05, "5": 0.6, "6": 0.1 }},
            "Act": {{ "0": 0.8, "1": 0.1, "2": 0.05, "3": 0.05 }}
        }}'''
        
        try:
            res = self.client.models.generate_content(
                model= self.MODEL_NAME, 
                contents=self.prompt)
            
            raw_output = res.text
            # Clean potential markdown backticks
            clean_string = re.sub(r'```json|```', '', raw_output).strip()
            
            # Use json.loads for standard JSON parsing
            import json
            data_dict = json.loads(clean_string)
            
            # Map string keys back to integers if necessary
            emotion_scores = {int(k): v for k, v in data_dict.get("Emotion", {}).items()}
            act_scores = {int(k): v for k, v in data_dict.get("Act", {}).items()}
            flag_sarcasm = data_dict.get("Is Sarcasm", False)

            return {
                "Is Sarcasm" : flag_sarcasm, 
                "Emotion Scores" : emotion_scores, 
                "Act Scores" : act_scores
            }

        except Exception as e:
            print(f"Gemini Prediction/Parsing failed: {e}")
            # Return a safe neutral default to prevent downstream crashes
            return {
                "Is Sarcasm": False,
                "Emotion Scores": {i: (1.0 if i==0 else 0.0) for i in range(7)},
                "Act Scores": {i: (1.0 if i==0 else 0.0) for i in range(4)}
            }
            
        