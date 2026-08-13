# features.py
# Prepare features for machine learning

# Tools used to prepare the data for machine learning
from sklearn.compose import ColumnTransformer
from sklearn.preprocessing import OneHotEncoder, StandardScaler

# Import our cleaning functions
from cleaning import load_data, clean_data


# Numerical columns
NUMERICAL_FEATURES = [
    "age",
    "balance",
    "day",
    "campaign",
    "pdays",
    "previous"
]


# Categorical columns
CATEGORICAL_FEATURES = [
    "job",
    "marital",
    "education",
    "default",
    "housing",
    "loan",
    "contact",
    "month",
    "poutcome"
]


def prepare_features(df):
    """
    Separate the input features from the target variable.

    The duration column is removed because call duration
    would only be known after the marketing call has ended.

    Therefore, using duration would not be suitable for
    predicting whether a customer will subscribe before
    the call takes place.
    """

    # X contains the features used for prediction
    X = df.drop(
        columns=[
            "target",
            "duration"
        ]
    )

    # y contains the target variable
    # 0 = No subscription
    # 1 = Subscription
    y = df["target"]

    return X, y


def build_preprocessor():
    """
    Create preprocessing steps for numerical
    and categorical features.

    Numerical features are standardized.

    Categorical features are converted into
    numerical values using one hot encoding.
    """

    # Standardize numerical columns
    numerical_processor = StandardScaler()

    # Convert categorical columns into numerical columns
    categorical_processor = OneHotEncoder(
        handle_unknown="ignore",
        sparse_output=False
    )

    # Apply preprocessing based on column type
    preprocessor = ColumnTransformer(
        transformers=[
            (
                "numerical",
                numerical_processor,
                NUMERICAL_FEATURES
            ),
            (
                "categorical",
                categorical_processor,
                CATEGORICAL_FEATURES
            )
        ]
    )

    return preprocessor


# Run this section only when features.py is run directly
if __name__ == "__main__":

    # Load original dataset
    df = load_data()

    # Clean dataset
    df = clean_data(df)

    # Separate features and target
    X, y = prepare_features(df)

    print("=" * 60)
    print("FEATURE PREPARATION")
    print("=" * 60)

    print()
    print("Feature preparation successful")

    print()
    print("Number of rows:")
    print(X.shape[0])

    print()
    print("Number of input features before encoding:")
    print(X.shape[1])

    print()
    print("Input columns:")
    print(X.columns.tolist())

    print()
    print("Numerical features:")
    print(NUMERICAL_FEATURES)

    print()
    print("Categorical features:")
    print(CATEGORICAL_FEATURES)

    print()
    print("Target distribution:")
    print(y.value_counts())

    print()
    print("Target percentage:")
    print(
        y.value_counts(normalize=True) * 100
    )