import pandas as pd
from datasets import Dataset

class Preprocessor():
    def __init__(self, df, tokenizer):
        self.df = df
        self.tokenizer = tokenizer
    
    def _column_processor(self):
        self.df['Act Label'] = self.df['Act Label']-1

        # Change None type to string
        self.df['Context'] = self.df['Context'].fillna("").astype(str)
        self.df['Text'] = self.df['Text'].fillna("").astype(str)

    def tokenization(self):
        self._column_processor()
        def preprocess(subset):
            model_inputs = self.tokenizer(
                subset['Context'],
                subset['Text'],
                max_length = 350,
                truncation = True,
                padding = False
            )
            model_inputs['label_emo'] = subset['Emotion Label']
            model_inputs['label_act'] = subset['Act Label']

            return model_inputs

        # Conversion to hugging face
        hf_data = Dataset.from_pandas(self.df)
        tokenized_data = hf_data.map(preprocess, batched=True, remove_columns=hf_data.column_names)

        return tokenized_data
    
        

    