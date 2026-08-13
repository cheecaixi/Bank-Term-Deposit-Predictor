# Import pandas to work with the dataset
import pandas as pd

# Import the dataset path from config.py
from config import DATA_PATH


# Rename the original V1 to V16 columns
# so that the column names are easier to understand
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


def load_data():
    """
    Load the bank marketing dataset.
    """

    # Read the CSV file
    df = pd.read_csv(DATA_PATH)

    return df


def clean_data(df):
    """
    Prepare the dataset for machine learning.
    """

    # Make a copy so we do not change the original dataset
    df = df.copy()

    # Rename the columns
    df = df.rename(columns=COLUMN_NAMES)

    # Remove duplicate rows if there are any
    df = df.drop_duplicates()

    # Change the target values:
    # Original 1 = No subscription
    # Original 2 = Yes subscription
    #
    # New 0 = No subscription
    # New 1 = Yes subscription
    df["target"] = df["target"].map({
        1: 0,
        2: 1
    })

    return df


# This section only runs when cleaning.py is run directly
if __name__ == "__main__":

    # Load the dataset
    df = load_data()

    # Clean the dataset
    df = clean_data(df)

    # Show basic information to check that everything worked
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