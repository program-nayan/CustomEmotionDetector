import requests 
import re
import os
import pandas as pd
from pathlib import Path
import zipfile
import shutil
import logging

# Set up logging to print to the terminal
logging.basicConfig(
    level=logging.INFO,
    format='%(message)s' 
)
logger = logging.getLogger(__name__)

class DataIngestion():
    def __init__(self, set):
        self.set = set 

    def _download_and_extract_data(self):
        '''Downloads and Extracts all the required datasplits cleanly in a Data folder'''
        # Create a folder where to store data
        data_path = Path('Data/')
        if data_path.is_dir():
            logger.info("Already a directory skipping creation")
        else:
            logger.info('Creating the directory')
            data_path.mkdir(parents=True, exist_ok=True)

        # Download the zipfile
        if Path(f'Data/{self.set}').is_dir():
            logger.info(f'{self.set} data already exists, skipping download and extraction')
        else:
            logger.info('Downloading the data...')
            if os.path.exists('Data/data.zip'):
                logger.info("Dataset already exists, skipping download !")
            else:
                url = 'https://aclanthology.org/attachments/I17-1099.Datasets.zip' 
                r = requests.get(url)
                with open('Data/data.zip', 'wb') as f:
                    f.write(r.content)

            # Extract all the zipfiles in the same directory
            logger.info("Extracting main zipfile...")
            with zipfile.ZipFile(file='Data/data.zip') as main_extractor:
                main_extractor.extractall(data_path)

            logger.info("Extracting Train Validation and Test datasets...")
            with zipfile.ZipFile(file='Data/EMNLP_dataset/train.zip') as train_extractor, \
                zipfile.ZipFile(file='Data/EMNLP_dataset/validation.zip') as validation_extractor, \
                zipfile.ZipFile(file='Data/EMNLP_dataset/test.zip') as test_extractor:
                train_extractor.extractall(data_path)
                validation_extractor.extractall(data_path)
                test_extractor.extractall(data_path)

            # Delete the main zipfile after extraction
            logger.info("Deleting unnecessary files and folders...")
            if os.path.exists('Data/data.zip'):
                os.remove('Data/data.zip')

            # Delete additional folders and extracted zipfiles
            shutil.rmtree('Data/__MACOSX', ignore_errors=True)
            shutil.rmtree('Data/EMNLP_dataset', ignore_errors=True)

    def build_master_datasets(self):
        self._download_and_extract_data()
        # If the data is already treated, return dataframe
        if Path(f'Data/{self.set}/df_{self.set}.csv').exists():
            return pd.read_csv(f'Data/{self.set}/df_{self.set}.csv')

        # Create rows and columns in dataframe and return it
        else:
            rows = []
            with open(f'Data/{self.set}/dialogues_{self.set}.txt', 'r', encoding='utf-8') as f_text, \
            open(f'Data/{self.set}/dialogues_act_{self.set}.txt', 'r', encoding='utf-8') as f_act, \
            open(f'Data/{self.set}/dialogues_emotion_{self.set}.txt', 'r', encoding='utf-8') as f_emotion:
                for conv_id, (t_line, e_line, a_line) in enumerate(zip(f_text, f_emotion, f_act)):
                    text = [t.strip() for t in t_line.split('__eou__') if t.strip()]
                    emotion = e_line.strip().split()
                    act = a_line.strip().split()
                    
                    if len(text) == len(emotion) == len(act):
                        for i in range(len(text)):
                            prev_text = text[i-1] if i!=0 else ""

                            rows.append(
                                {
                                    'Conversation Id' : conv_id,
                                    'Turn' : i,
                                    'Text' : text[i],
                                    'Context' : prev_text,
                                    'Emotion Label' : int(emotion[i]),
                                    'Act Label' : int(act[i])
                                }
                            ) 

                    else:
                        logger.warning(f'Skipping addition of conv_id:{conv_id} of {self.set} set due to length mismatch')

            df = pd.DataFrame(rows)   
            df.to_csv(f'Data/{self.set}/df_{self.set}.csv')
            logger.info(f"Sucessfully added {len(df)} turn to {self.set} data !")             

        return df
