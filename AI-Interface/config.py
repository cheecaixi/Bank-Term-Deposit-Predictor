# config.py
# Keep shared paths and model settings in one place so training,
# evaluation, and inference use the same configuration.

import os


# ============================================================
# PROJECT PATHS
# ============================================================

# Folder containing config.py
AI_INTERFACE_DIR = os.path.dirname(
    os.path.abspath(__file__)
)


# Main project folder
PROJECT_ROOT = os.path.dirname(
    AI_INTERFACE_DIR
)


# ============================================================
# REPRODUCIBLE TRAINING SETTINGS
# ============================================================

# Reusing this seed keeps data splits and model searches repeatable.
RANDOM_STATE = 42


# Dataset location
DATA_PATH = os.path.join(
    PROJECT_ROOT,
    "data",
    "Bank_Marketing_Dataset.csv"
)


# ============================================================
# DEPLOYED MODEL SETTINGS
# ============================================================

# Probabilities at or above this value become a Yes prediction.
PREDICTION_THRESHOLD = 0.6

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


# ============================================================
# FASTAPI SERVICE SETTINGS
# ============================================================

# API settings
API_HOST = "0.0.0.0"

API_PORT = 7000
