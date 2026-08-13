import pandas as pd

from config import DATA_PATH


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

    df = pd.read_csv(DATA_PATH)

    return df


def clean_data(df):
    """
    Prepare the dataset for machine learning.
    """

    df = df.copy()

    df = df.rename(
        columns=COLUMN_NAMES
    )

    df = df.drop_duplicates()

    df["target"] = df["target"].map({
        1: 0,
        2: 1
    })

    return df


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