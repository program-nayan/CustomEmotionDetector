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
        Categorize the given text : {text} and the context {context} into given emotions : {self.emo_map} and actions : {self.act_map}.
        Constraints :
        1. STRICTLY RETURN A JSON OBJECT NOTHING ELSE
        2. RETURN THE ANSWER IN THE FORMAT PROVIDED IN THE EXAMPLE
        3. Sarcasm value should be boolean (first letter capitalised)
        5. Do not put label number in inverted commas "0" put it in integer format like 0
        Task : 
        Return a JSON object containing the following data : Emotion labels and their probabilities, Act labels and their probabilities.
        Example : 
        Input = > {{Context : My close friend died yesterday,  Text : I don't know what to say}}
        Output = >  {{ 
            {{Is Sarcasm : True}},
        {{Emotion : {{ 0 : 0.13, 1 : 0.04, 2 : 0.11, 3 : 0.05, 4 : 0.01, 5 : 0.65, 6 : 0.01}} }}, 
        {{Act : {{ 0 : 0.73, 1 : 0.20, 2 : 0.04, 3 : 0.03}}}}
        }}'''
        
        res = self.client.models.generate_content(
            model= self.MODEL_NAME, 
            contents=self.prompt)


        # 1. Clean the markdown backticks from the string
        raw_output = res.text
        clean_string = re.sub(r'```json|```', '', raw_output).strip()

        # 2. Parse using ast.literal_eval (safe for Python-style literals)
        try:
            data_dict = ast.literal_eval(clean_string)
            
            # 3. Extract your variables
            flag_sarcasm = data_dict.get("Is Sarcasm", False)
            emotion_scores = data_dict.get("Emotion", {})
            act_scores  = data_dict.get("Act", {})

            return {
                "Is Sarcasm" : flag_sarcasm, 
                "Emotion Scores" : emotion_scores, 
                "Act Scores" : act_scores
            }

        except (ValueError, SyntaxError) as e:
            print(f"Parsing failed: {e}")
            return res
            
        