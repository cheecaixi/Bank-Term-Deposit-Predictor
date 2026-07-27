"""
Train and compare three models for the Bank Marketing dataset:

1. Logistic Regression
2. Random Forest
3. XGBoost

The script:
- loads and cleans the dataset;
- renames V1-V16 into meaningful feature names;
- creates preprocessing pipelines;
- trains all three models;
- compares Accuracy, Precision, Recall, F1-score and ROC-AUC;
- selects the best model based on F1-score;
- saves the best complete pipeline for the inference service;
- saves each trained model and the comparison results.

Install requirements:
    pip install pandas scikit-learn joblib xgboost

Run:
    python train_model.py
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import joblib
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import RandomForestClassifier
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    accuracy_score,
    classification_report,
    confusion_matrix,
    f1_score,
    precision_score,
    recall_score,
    roc_auc_score,
)
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler

try:
    from xgboost import XGBClassifier
except ImportError as exc:
    raise ImportError(
        "XGBoost is not installed. Run: pip install xgboost"
    ) from exc


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
DATA_PATH = Path("data") / "Bank_Marketing_Dataset.csv"
OUTPUT_DIR = Path("models")

BEST_MODEL_PATH = OUTPUT_DIR / "best_model.joblib"
BEST_MODEL_INFO_PATH = OUTPUT_DIR / "best_model_info.json"
COMPARISON_CSV_PATH = OUTPUT_DIR / "model_comparison.csv"
COMPARISON_JSON_PATH = OUTPUT_DIR / "model_comparison.json"

RANDOM_STATE = 42
TEST_SIZE = 0.20

# The best model is selected using F1-score because the target classes are
# imbalanced and accuracy alone may be misleading.
SELECTION_METRIC = "f1_score"


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
    "Class": "subscribed",
}


# ---------------------------------------------------------------------------
# Data loading and cleaning
# ---------------------------------------------------------------------------

def load_data(path: Path) -> pd.DataFrame:
    """Load the dataset and rename its columns."""
    if not path.exists():
        raise FileNotFoundError(
            f"Dataset not found at: {path.resolve()}\n"
            "Place Bank_Marketing_Dataset.csv in the same folder as this script."
        )

    df = pd.read_csv(path)

    missing_columns = set(COLUMN_NAMES) - set(df.columns)
    if missing_columns:
        raise ValueError(
            "The dataset is missing expected columns: "
            f"{sorted(missing_columns)}"
        )

    return df.rename(columns=COLUMN_NAMES)


def clean_data(df: pd.DataFrame) -> pd.DataFrame:
    """Clean text values, remove duplicates and convert the target to 0/1."""
    cleaned = df.copy()

    categorical_columns = cleaned.select_dtypes(include="object").columns
    for column in categorical_columns:
        cleaned[column] = (
            cleaned[column]
            .astype(str)
            .str.strip()
            .str.lower()
        )

    duplicate_count = int(cleaned.duplicated().sum())
    cleaned = cleaned.drop_duplicates().reset_index(drop=True)

    # Original values:
    # 1 = no subscription
    # 2 = subscription
    cleaned["subscribed"] = cleaned["subscribed"].map({1: 0, 2: 1})

    if cleaned["subscribed"].isna().any():
        unexpected = df.loc[
            cleaned["subscribed"].isna(), "subscribed"
        ].unique()
        raise ValueError(
            f"Unexpected target values found: {unexpected.tolist()}"
        )

    print("=" * 70)
    print("DATASET INFORMATION")
    print("=" * 70)
    print(f"Rows after cleaning: {len(cleaned):,}")
    print(f"Columns: {cleaned.shape[1]}")
    print(f"Duplicate rows removed: {duplicate_count}")
    print("\nTarget distribution:")
    print(
        cleaned["subscribed"]
        .value_counts()
        .rename(index={0: "No", 1: "Yes"})
    )

    return cleaned


# ---------------------------------------------------------------------------
# Preprocessing and models
# ---------------------------------------------------------------------------

def build_preprocessor(
    numerical_features: list[str],
    categorical_features: list[str],
) -> ColumnTransformer:
    """Create preprocessing steps for numeric and categorical features."""
    numerical_pipeline = Pipeline(
        steps=[
            ("imputer", SimpleImputer(strategy="median")),
            ("scaler", StandardScaler()),
        ]
    )

    categorical_pipeline = Pipeline(
        steps=[
            ("imputer", SimpleImputer(strategy="most_frequent")),
            (
                "onehot",
                OneHotEncoder(
                    handle_unknown="ignore",
                    sparse_output=True,
                ),
            ),
        ]
    )

    return ColumnTransformer(
        transformers=[
            ("numerical", numerical_pipeline, numerical_features),
            ("categorical", categorical_pipeline, categorical_features),
        ]
    )


def get_models() -> dict[str, Any]:
    """Return the three classifiers to be compared."""
    return {
        "Logistic Regression": LogisticRegression(
            max_iter=2000,
            class_weight="balanced",
            random_state=RANDOM_STATE,
        ),
        "Random Forest": RandomForestClassifier(
            n_estimators=300,
            class_weight="balanced",
            random_state=RANDOM_STATE,
            n_jobs=-1,
        ),
        "XGBoost": XGBClassifier(
            n_estimators=300,
            learning_rate=0.05,
            max_depth=6,
            min_child_weight=1,
            subsample=0.8,
            colsample_bytree=0.8,
            objective="binary:logistic",
            eval_metric="logloss",
            random_state=RANDOM_STATE,
            n_jobs=-1,
        ),
    }


# ---------------------------------------------------------------------------
# Training and evaluation
# ---------------------------------------------------------------------------

def evaluate_model(
    model_name: str,
    pipeline: Pipeline,
    X_test: pd.DataFrame,
    y_test: pd.Series,
) -> dict[str, Any]:
    """Calculate classification metrics for one trained model."""
    predictions = pipeline.predict(X_test)
    probabilities = pipeline.predict_proba(X_test)[:, 1]

    metrics = {
        "model": model_name,
        "accuracy": float(accuracy_score(y_test, predictions)),
        "precision": float(
            precision_score(y_test, predictions, zero_division=0)
        ),
        "recall": float(
            recall_score(y_test, predictions, zero_division=0)
        ),
        "f1_score": float(
            f1_score(y_test, predictions, zero_division=0)
        ),
        "roc_auc": float(roc_auc_score(y_test, probabilities)),
        "confusion_matrix": confusion_matrix(
            y_test, predictions
        ).tolist(),
    }

    print("\n" + "=" * 70)
    print(model_name.upper())
    print("=" * 70)
    print(f"Accuracy : {metrics['accuracy']:.4f}")
    print(f"Precision: {metrics['precision']:.4f}")
    print(f"Recall   : {metrics['recall']:.4f}")
    print(f"F1-score : {metrics['f1_score']:.4f}")
    print(f"ROC-AUC  : {metrics['roc_auc']:.4f}")
    print(f"Confusion matrix: {metrics['confusion_matrix']}")

    print("\nClassification report:")
    print(
        classification_report(
            y_test,
            predictions,
            target_names=["No subscription", "Subscription"],
            zero_division=0,
        )
    )

    return metrics


def train_and_compare(
    X_train: pd.DataFrame,
    X_test: pd.DataFrame,
    y_train: pd.Series,
    y_test: pd.Series,
    numerical_features: list[str],
    categorical_features: list[str],
) -> tuple[dict[str, Pipeline], list[dict[str, Any]]]:
    """Train all models and return trained pipelines and their results."""
    trained_pipelines: dict[str, Pipeline] = {}
    results: list[dict[str, Any]] = []

    for model_name, classifier in get_models().items():
        print(f"\nTraining {model_name}...")

        # A separate preprocessor is created for each model so each saved
        # pipeline is fully independent.
        preprocessor = build_preprocessor(
            numerical_features,
            categorical_features,
        )

        pipeline = Pipeline(
            steps=[
                ("preprocessor", preprocessor),
                ("model", classifier),
            ]
        )

        pipeline.fit(X_train, y_train)

        metrics = evaluate_model(
            model_name,
            pipeline,
            X_test,
            y_test,
        )

        trained_pipelines[model_name] = pipeline
        results.append(metrics)

    return trained_pipelines, results


# ---------------------------------------------------------------------------
# Saving outputs
# ---------------------------------------------------------------------------

def safe_filename(model_name: str) -> str:
    """Convert a model name into a safe filename."""
    return model_name.lower().replace(" ", "_")


def save_outputs(
    trained_pipelines: dict[str, Pipeline],
    results: list[dict[str, Any]],
) -> str:
    """Save all models, comparison results and the best model."""
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    # Save every model pipeline.
    for model_name, pipeline in trained_pipelines.items():
        model_path = OUTPUT_DIR / f"{safe_filename(model_name)}.joblib"
        joblib.dump(pipeline, model_path)
        print(f"Saved {model_name}: {model_path}")

    # Save results without the nested confusion matrix in the CSV.
    comparison_df = pd.DataFrame(
        [
            {
                "model": item["model"],
                "accuracy": item["accuracy"],
                "precision": item["precision"],
                "recall": item["recall"],
                "f1_score": item["f1_score"],
                "roc_auc": item["roc_auc"],
            }
            for item in results
        ]
    ).sort_values(
        by=SELECTION_METRIC,
        ascending=False,
    )

    comparison_df.to_csv(COMPARISON_CSV_PATH, index=False)

    with COMPARISON_JSON_PATH.open("w", encoding="utf-8") as file:
        json.dump(results, file, indent=4)

    best_row = comparison_df.iloc[0]
    best_model_name = str(best_row["model"])
    best_pipeline = trained_pipelines[best_model_name]

    joblib.dump(best_pipeline, BEST_MODEL_PATH)

    best_model_info = {
        "best_model": best_model_name,
        "selection_metric": SELECTION_METRIC,
        "selection_score": float(best_row[SELECTION_METRIC]),
        "metrics": {
            key: float(best_row[key])
            for key in [
                "accuracy",
                "precision",
                "recall",
                "f1_score",
                "roc_auc",
            ]
        },
    }

    with BEST_MODEL_INFO_PATH.open("w", encoding="utf-8") as file:
        json.dump(best_model_info, file, indent=4)

    print("\n" + "=" * 70)
    print("MODEL COMPARISON")
    print("=" * 70)
    print(comparison_df.to_string(index=False))

    print("\n" + "=" * 70)
    print("BEST MODEL")
    print("=" * 70)
    print(f"Selected model: {best_model_name}")
    print(
        f"Selected by {SELECTION_METRIC}: "
        f"{float(best_row[SELECTION_METRIC]):.4f}"
    )
    print(f"Best model saved to: {BEST_MODEL_PATH}")
    print(f"Comparison CSV saved to: {COMPARISON_CSV_PATH}")
    print(f"Comparison JSON saved to: {COMPARISON_JSON_PATH}")

    return best_model_name


# ---------------------------------------------------------------------------
# Example prediction
# ---------------------------------------------------------------------------

def test_example_customer(best_pipeline: Pipeline) -> None:
    """Make one example prediction using the selected best model."""
    example_customer = pd.DataFrame(
        [
            {
                "age": 42,
                "job": "technician",
                "marital": "married",
                "education": "secondary",
                "default": "no",
                "balance": 1500,
                "housing": "yes",
                "loan": "no",
                "contact": "cellular",
                "day": 15,
                "month": "may",
                "duration": 350,
                "campaign": 2,
                "pdays": -1,
                "previous": 0,
                "poutcome": "unknown",
            }
        ]
    )

    prediction = int(best_pipeline.predict(example_customer)[0])
    probability = float(
        best_pipeline.predict_proba(example_customer)[0, 1]
    )

    print("\n" + "=" * 70)
    print("EXAMPLE CUSTOMER PREDICTION")
    print("=" * 70)
    print(
        "Prediction:",
        "Yes, likely to subscribe"
        if prediction == 1
        else "No, unlikely to subscribe",
    )
    print(f"Subscription probability: {probability:.2%}")


# ---------------------------------------------------------------------------
# Main program
# ---------------------------------------------------------------------------

def main() -> None:
    df = load_data(DATA_PATH)
    df = clean_data(df)

    X = df.drop(columns=["subscribed"])
    y = df["subscribed"]

    numerical_features = X.select_dtypes(
        include=["int64", "float64"]
    ).columns.tolist()

    categorical_features = X.select_dtypes(
        include=["object", "category"]
    ).columns.tolist()

    print("\nNumerical features:")
    print(numerical_features)

    print("\nCategorical features:")
    print(categorical_features)

    X_train, X_test, y_train, y_test = train_test_split(
        X,
        y,
        test_size=TEST_SIZE,
        random_state=RANDOM_STATE,
        stratify=y,
    )

    print(f"\nTraining rows: {len(X_train):,}")
    print(f"Testing rows : {len(X_test):,}")

    trained_pipelines, results = train_and_compare(
        X_train,
        X_test,
        y_train,
        y_test,
        numerical_features,
        categorical_features,
    )

    best_model_name = save_outputs(
        trained_pipelines,
        results,
    )

    best_pipeline = trained_pipelines[best_model_name]
    test_example_customer(best_pipeline)


if __name__ == "__main__":
    main()