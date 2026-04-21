from data_ingestion import DataIngestion
from preprocessing import Preprocessor
from transformers import AutoTokenizer, AutoConfig
from setting_model_weights import CustomWeights
from modelling import MultiTaskRoberta
from model_trainer import ModelTrainer
from transformers import RobertaModel

if __name__ == "__main__":

    # 1. Data collection

    # invoke data ingestion class
    train_ingestor = DataIngestion(set='train')
    validation_ingestor = DataIngestion(set='validation')
    test_ingestor = DataIngestion(set='test')

    # Create datasets
    df_train = train_ingestor.build_master_datasets()
    df_validation = validation_ingestor.build_master_datasets()
    df_test = test_ingestor.build_master_datasets()


    # 2. Data preprocessing

    # Initializing tokenizer
    model_used = 'FacebookAI/roberta-base'
    tokenizer = AutoTokenizer.from_pretrained(model_used)

    # Creating Processor events
    train_tokenizer = Preprocessor(df=df_train, tokenizer=tokenizer)
    val_tokenizer = Preprocessor(df=df_validation, tokenizer=tokenizer)
    test_tokenizer = Preprocessor(df=df_test, tokenizer=tokenizer)

    tokenized_train = train_tokenizer.tokenization()
    tokenized_val = val_tokenizer.tokenization()
    tokenized_test= test_tokenizer.tokenization()

    
    # 3. Creating the model
    
    # Setting custom weights
    custom_weights = CustomWeights(df=df_train)
    config = custom_weights.custom_weight_calculation()

    # Creating instance of model
    model_0 = MultiTaskRoberta.from_pretrained("FacebookAI/roberta-base", config=config)


    # 4. Model Training

    # Create trainer object
    trainer_object = ModelTrainer(model=model_0, epochs=4, tokenizer=tokenizer)
    trainer = trainer_object.get_trainer(train_data=tokenized_train, validation_data=tokenized_val)

    # Start training
    # In main_engine.py

    # Start training
    train_result = trainer.train()
    print("\nTraining complete!")

    # Access metrics from the training result
    final_metrics = train_result.metrics
    print(f"Final Best Metric: {final_metrics.get('eval_emo_f1_macro')}")

    # Save model
    print("\nSaving the model and tokenizer to disk...")
    save_directory = "./custom_roberta_multitask_final"
    trainer.save_model(save_directory)
    tokenizer.save_pretrained(save_directory)

    print(f"Model successfully saved to {save_directory}. Ready for deployment!")