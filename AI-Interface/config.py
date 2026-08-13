import os


# Folder containing config.py
AI_INTERFACE_DIR = os.path.dirname(
    os.path.abspath(__file__)
)


# Main project folder
PROJECT_ROOT = os.path.dirname(
    AI_INTERFACE_DIR
)


# Random seed
RANDOM_STATE = 42


# Dataset location
DATA_PATH = os.path.join(
    PROJECT_ROOT,
    "data",
    "Bank_Marketing_Dataset.csv"
)


# Prediction threshold
PREDICTION_THRESHOLD = 0.20


# Saved model location
MODEL_PATH = os.path.join(
    AI_INTERFACE_DIR,
    "models",
    "best_model.joblib"
)


# Model information
MODEL_NAME = "Bank Term Deposit Prediction Model"

MODEL_VERSION = "1.0"

NUMBER_OF_FEATURES = 15


# API settings
API_HOST = "0.0.0.0"

API_PORT = 7000