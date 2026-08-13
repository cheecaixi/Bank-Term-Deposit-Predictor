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
    RocCurveDisplay,
    PrecisionRecallDisplay
)

# Import project functions
from cleaning import load_data, clean_data
from features import prepare_features

# Import shared configuration
from config import (
    RANDOM_STATE,
    PREDICTION_THRESHOLD,
    MODEL_PATH,
    AI_INTERFACE_DIR
)


# Folder for evaluation results
RESULTS_FOLDER = os.path.join(
    AI_INTERFACE_DIR,
    "results",
    "evaluation"
)


def load_model():
    """
    Load the saved final machine learning model.
    """

    if not os.path.exists(MODEL_PATH):
        raise FileNotFoundError(
            f"Model file not found: {MODEL_PATH}"
        )

    model = joblib.load(
        MODEL_PATH
    )

    print("Model loaded successfully:")
    print(MODEL_PATH)

    return model


def prepare_test_data():
    """
    Load, clean, and prepare the dataset.

    The same train and test split used during training
    is recreated using the same random state.
    """

    # Load dataset
    df = load_data()

    # Clean dataset
    df = clean_data(df)

    # Separate features and target
    X, y = prepare_features(df)

    # Recreate the same train and test split
    (
        X_train,
        X_test,
        y_train,
        y_test
    ) = train_test_split(
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
        y_probability >= PREDICTION_THRESHOLD
    ).astype(int)

    # Calculate evaluation metrics
    results = {

        "Accuracy": accuracy_score(
            y_test,
            y_pred
        ),

        "Precision": precision_score(
            y_test,
            y_pred,
            zero_division=0
        ),

        "Recall": recall_score(
            y_test,
            y_pred,
            zero_division=0
        ),

        "F1 Score": f1_score(
            y_test,
            y_pred,
            zero_division=0
        ),

        "ROC AUC": roc_auc_score(
            y_test,
            y_probability
        )
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
    Display evaluation results in the terminal.
    """

    print()
    print("=" * 60)
    print("FINAL MODEL EVALUATION")
    print("=" * 60)

    print()
    print(
        f"Threshold: "
        f"{PREDICTION_THRESHOLD}"
    )

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

    # Add threshold to saved results
    results_df.insert(
        0,
        "Threshold",
        PREDICTION_THRESHOLD
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


def create_precision_recall_curve(
    y_test,
    y_probability
):
    """
    Create and save the precision recall curve.

    This is especially useful because the target
    variable is imbalanced.
    """

    os.makedirs(
        RESULTS_FOLDER,
        exist_ok=True
    )

    PrecisionRecallDisplay.from_predictions(
        y_test,
        y_probability
    )

    plt.title(
        "Precision Recall Curve"
    )

    plt.tight_layout()

    file_path = os.path.join(
        RESULTS_FOLDER,
        "precision_recall_curve.png"
    )

    plt.savefig(
        file_path,
        dpi=300
    )

    plt.close()

    print()
    print("Precision recall curve saved:")
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

    # Save evaluation metrics
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

    # Create precision recall curve
    create_precision_recall_curve(
        y_test,
        y_probability
    )

    print()
    print("=" * 60)
    print("EVALUATION COMPLETED SUCCESSFULLY")
    print("=" * 60)

    print()
    print("Results saved in:")
    print(RESULTS_FOLDER)


if __name__ == "__main__":
    main()