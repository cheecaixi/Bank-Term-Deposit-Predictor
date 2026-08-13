# evaluate.py
# Evaluate the final trained bank term deposit prediction model

import os
import joblib
import pandas as pd
import matplotlib.pyplot as plt

from sklearn.model_selection import train_test_split

from sklearn.metrics import (
    accuracy_score,
    precision_score,
    recall_score,
    f1_score,
    roc_auc_score,
    classification_report,
    confusion_matrix,
    ConfusionMatrixDisplay,
    RocCurveDisplay
)

# Import project functions
from cleaning import load_data, clean_data
from features import prepare_features


# Configuration
RANDOM_STATE = 42

# Final classification threshold
THRESHOLD = 0.20

# Saved model location
MODEL_PATH = os.path.join(
    "models",
    "best_model.joblib"
)

# Folder for evaluation results
RESULTS_FOLDER = os.path.join(
    "results",
    "evaluation"
)


def load_model():
    """
    Load the trained machine learning model.
    """

    model = joblib.load(
        MODEL_PATH
    )

    print("Model loaded successfully:")
    print(MODEL_PATH)

    return model


def prepare_test_data():
    """
    Load and prepare the dataset.

    The same train test split used during model training
    is recreated using the same random state.
    """

    # Load dataset
    df = load_data()

    # Clean dataset
    df = clean_data(df)

    # Prepare features and target
    X, y = prepare_features(df)

    # Recreate the same train test split
    X_train, X_test, y_train, y_test = train_test_split(
        X,
        y,
        test_size=0.20,
        random_state=RANDOM_STATE,
        stratify=y
    )

    return X_test, y_test


def calculate_metrics(
    model,
    X_test,
    y_test
):
    """
    Calculate evaluation metrics for the final model.
    """

    # Predict probability of subscription
    y_probability = model.predict_proba(
        X_test
    )[:, 1]

    # Convert probability into class prediction
    y_pred = (
        y_probability >= THRESHOLD
    ).astype(int)

    # Calculate evaluation metrics
    accuracy = accuracy_score(
        y_test,
        y_pred
    )

    precision = precision_score(
        y_test,
        y_pred,
        zero_division=0
    )

    recall = recall_score(
        y_test,
        y_pred,
        zero_division=0
    )

    f1 = f1_score(
        y_test,
        y_pred,
        zero_division=0
    )

    roc_auc = roc_auc_score(
        y_test,
        y_probability
    )

    results = {
        "Accuracy": accuracy,
        "Precision": precision,
        "Recall": recall,
        "F1 Score": f1,
        "ROC AUC": roc_auc
    }

    return (
        results,
        y_pred,
        y_probability
    )


def print_results(
    results,
    y_test,
    y_pred
):
    """
    Display evaluation results.
    """

    print()
    print("=" * 60)
    print("FINAL MODEL EVALUATION")
    print("=" * 60)

    print()
    print(f"Threshold: {THRESHOLD}")

    print()

    print(
        f"Accuracy:  "
        f"{results['Accuracy']:.4f}"
    )

    print(
        f"Precision: "
        f"{results['Precision']:.4f}"
    )

    print(
        f"Recall:    "
        f"{results['Recall']:.4f}"
    )

    print(
        f"F1 Score:  "
        f"{results['F1 Score']:.4f}"
    )

    print(
        f"ROC AUC:   "
        f"{results['ROC AUC']:.4f}"
    )

    print()
    print("Classification Report:")

    print(
        classification_report(
            y_test,
            y_pred,
            target_names=[
                "No Subscription",
                "Subscription"
            ],
            zero_division=0
        )
    )


def save_metrics(results):
    """
    Save evaluation metrics into a CSV file.
    """

    os.makedirs(
        RESULTS_FOLDER,
        exist_ok=True
    )

    results_df = pd.DataFrame(
        [results]
    )

    file_path = os.path.join(
        RESULTS_FOLDER,
        "final_metrics.csv"
    )

    results_df.to_csv(
        file_path,
        index=False
    )

    print()
    print("Metrics saved:")
    print(file_path)


def create_confusion_matrix(
    y_test,
    y_pred
):
    """
    Create and save the confusion matrix.
    """

    os.makedirs(
        RESULTS_FOLDER,
        exist_ok=True
    )

    cm = confusion_matrix(
        y_test,
        y_pred
    )

    display = ConfusionMatrixDisplay(
        confusion_matrix=cm,
        display_labels=[
            "No Subscription",
            "Subscription"
        ]
    )

    display.plot()

    plt.title(
        "Confusion Matrix"
    )

    plt.tight_layout()

    file_path = os.path.join(
        RESULTS_FOLDER,
        "confusion_matrix.png"
    )

    plt.savefig(
        file_path,
        dpi=300
    )

    plt.close()

    print()
    print("Confusion matrix saved:")
    print(file_path)


def create_roc_curve(
    y_test,
    y_probability
):
    """
    Create and save the ROC curve.
    """

    os.makedirs(
        RESULTS_FOLDER,
        exist_ok=True
    )

    RocCurveDisplay.from_predictions(
        y_test,
        y_probability
    )

    plt.title(
        "ROC Curve"
    )

    plt.tight_layout()

    file_path = os.path.join(
        RESULTS_FOLDER,
        "roc_curve.png"
    )

    plt.savefig(
        file_path,
        dpi=300
    )

    plt.close()

    print()
    print("ROC curve saved:")
    print(file_path)


def main():

    print("=" * 60)
    print("BANK TERM DEPOSIT MODEL EVALUATION")
    print("=" * 60)

    # Load trained model
    model = load_model()

    # Prepare test dataset
    X_test, y_test = prepare_test_data()

    print()
    print("Testing rows:")
    print(len(X_test))

    # Evaluate model
    (
        results,
        y_pred,
        y_probability
    ) = calculate_metrics(
        model,
        X_test,
        y_test
    )

    # Display results
    print_results(
        results,
        y_test,
        y_pred
    )

    # Save evaluation results
    save_metrics(
        results
    )

    # Create confusion matrix
    create_confusion_matrix(
        y_test,
        y_pred
    )

    # Create ROC curve
    create_roc_curve(
        y_test,
        y_probability
    )

    print()
    print("=" * 60)
    print("EVALUATION COMPLETED SUCCESSFULLY")
    print("=" * 60)


if __name__ == "__main__":
    main()