# cleaning.py
# Load the raw dataset and convert it into a consistent format
# for feature preparation and model training.

import pandas as pd

from config import DATA_PATH


# The source CSV uses generic V1-V16 headings. This mapping
# gives every column a meaningful business name.
COLUMN_NAMES = {
    "V1": "age",
    "V2": "job",
    "V3": "marital",
    "V4": "education",
    "V5": "default",
    "V6": "balance",
    "V7": "housing",
    "V8": "loan",
    "V9": "contact",
    "V10": "day",
    "V11": "month",
    "V12": "duration",
    "V13": "campaign",
    "V14": "pdays",
    "V15": "previous",
    "V16": "poutcome",
    "Class": "target"
}


# ============================================================
# 1. LOAD THE SOURCE DATA
# ============================================================

def load_data():
    """
    Load the bank marketing dataset.
    """

    df = pd.read_csv(DATA_PATH)

    return df


# ============================================================
# 2. APPLY REPEATABLE CLEANING RULES
# ============================================================

def clean_data(df):
    """
    Prepare the dataset for machine learning.
    """

    # Work on a copy so the original DataFrame is not modified.
    df = df.copy()

    # Replace generic source headings with readable names.
    df = df.rename(
        columns=COLUMN_NAMES
    )

    # Repeated records could bias the trained model.
    df = df.drop_duplicates()

    # Convert the original labels into the binary format used
    # by the classifiers: 0 = No and 1 = Yes.
    df["target"] = df["target"].map({
        1: 0,
        2: 1
    })

    return df


# Running this file directly performs a quick cleaning check.
if __name__ == "__main__":

    df = load_data()

    df = clean_data(df)

    print("Dataset loaded successfully")
    print()

    print("Dataset size:")
    print(df.shape)
    print()

    print("Missing values:")
    print(df.isnull().sum().sum())
    print()

    print("Duplicate rows:")
    print(df.duplicated().sum())
    print()

    print("Target values:")
    print(df["target"].value_counts())
    print()

    print("First 5 rows:")
    print(df.head())
