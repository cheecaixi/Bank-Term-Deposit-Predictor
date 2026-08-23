# train.py
# Train, tune, compare, and save machine learning models
# for bank term deposit prediction
#
# Training flow used during the code walkthrough:
# 1. Load and clean the dataset.
# 2. Split the data while preserving the target distribution.
# 3. Tune and evaluate four classification models.
# 4. Select the best model by ROC AUC and save it for the API.

import os
import joblib
import pandas as pd
from training.cleaning import load_data, clean_data
from training.features import prepare_features, build_preprocessor

from sklearn.model_selection import (
    train_test_split,
    RandomizedSearchCV,
    StratifiedKFold,
    cross_val_predict
)

from sklearn.ensemble import (
    RandomForestClassifier,
    GradientBoostingClassifier
)

from sklearn.metrics import (
    accuracy_score,
    precision_score,
    recall_score,
    f1_score,
    roc_auc_score,
    classification_report
)

from imblearn.pipeline import Pipeline as ImbPipeline
from imblearn.over_sampling import SMOTE

from xgboost import XGBClassifier
from lightgbm import LGBMClassifier


from config import (
    RANDOM_STATE,
    MODEL_PATH,
    AI_INTERFACE_DIR
)

MODEL_FOLDER = os.path.join(
    AI_INTERFACE_DIR,
    "models"
)


# ============================================================
# 1. DATA SPLITTING AND CLASS-IMBALANCE HELPERS
# ============================================================

def split_dataset(X, y):
    """
    Split the dataset into training and testing data.

    Stratify keeps approximately the same target
    distribution in both datasets.
    """

    X_train, X_test, y_train, y_test = train_test_split(
        X,
        y,
        test_size=0.20,
        random_state=RANDOM_STATE,
        stratify=y
    )

    return X_train, X_test, y_train, y_test


def calculate_scale_pos_weight(y_train):
    """
    Calculate the imbalance ratio for XGBoost.

    This is the number of negative samples divided
    by the number of positive samples.
    """

    negative = (y_train == 0).sum()
    positive = (y_train == 1).sum()

    return negative / positive


# ============================================================
# 2. MODEL PIPELINES AND SEARCH SPACES
# ============================================================

def create_model_configs(scale_pos_weight):
    """
    Create each model together with its tuning parameters.

    Different imbalance handling methods are used because
    each algorithm responds differently to imbalance.
    """

    model_configs = {

        # Random Forest handles imbalance by assigning more
        # importance to the minority subscription class.
        "Random Forest": {

            "pipeline": ImbPipeline(
                steps=[
                    (
                        "preprocessor",
                        build_preprocessor()
                    ),
                    (
                        "classifier",
                        RandomForestClassifier(
                            class_weight="balanced",
                            random_state=RANDOM_STATE,
                            n_jobs=-1
                        )
                    )
                ]
            ),

            "params": {
                "classifier__n_estimators": [
                    200,
                    300,
                    400,
                    500
                ],

                "classifier__max_depth": [
                    8,
                    10,
                    12,
                    15,
                    None
                ],

                "classifier__min_samples_split": [
                    2,
                    5,
                    10
                ],

                "classifier__min_samples_leaf": [
                    1,
                    2,
                    4
                ]
            }
        },


        # Gradient Boosting uses SMOTE inside the pipeline so
        # oversampling happens only on training folds.
        "Gradient Boosting": {

            "pipeline": ImbPipeline(
                steps=[
                    (
                        "preprocessor",
                        build_preprocessor()
                    ),
                    (
                        "smote",
                        SMOTE(
                            sampling_strategy=0.5,
                            random_state=RANDOM_STATE
                        )
                    ),
                    (
                        "classifier",
                        GradientBoostingClassifier(
                            random_state=RANDOM_STATE
                        )
                    )
                ]
            ),

            "params": {
                "classifier__n_estimators": [
                    150,
                    200,
                    250,
                    300
                ],

                "classifier__max_depth": [
                    2,
                    3,
                    4
                ],

                "classifier__learning_rate": [
                    0.03,
                    0.05,
                    0.08
                ],

                "classifier__min_samples_split": [
                    2,
                    5,
                    10
                ]
            }
        },


        # XGBoost uses the calculated negative-to-positive
        # ratio to give the minority class more influence.
        "XGBoost": {

            "pipeline": ImbPipeline(
                steps=[
                    (
                        "preprocessor",
                        build_preprocessor()
                    ),
                    (
                        "classifier",
                        XGBClassifier(
                            scale_pos_weight=scale_pos_weight,
                            eval_metric="logloss",
                            random_state=RANDOM_STATE,
                            n_jobs=-1
                        )
                    )
                ]
            ),

            "params": {
                "classifier__n_estimators": [
                    200,
                    300,
                    400,
                    500
                ],

                "classifier__max_depth": [
                    3,
                    4,
                    5,
                    6
                ],

                "classifier__learning_rate": [
                    0.02,
                    0.03,
                    0.05,
                    0.08
                ],

                "classifier__subsample": [
                    0.7,
                    0.8,
                    0.9,
                    1.0
                ],

                "classifier__colsample_bytree": [
                    0.7,
                    0.8,
                    0.9,
                    1.0
                ]
            }
        },


        # LightGBM uses balanced class weights while keeping
        # training efficient for the larger dataset.
        "LightGBM": {

            "pipeline": ImbPipeline(
                steps=[
                    (
                        "preprocessor",
                        build_preprocessor()
                    ),
                    (
                        "classifier",
                        LGBMClassifier(
                            class_weight="balanced",
                            random_state=RANDOM_STATE,
                            verbosity=-1
                        )
                    )
                ]
            ),

            "params": {
                "classifier__n_estimators": [
                    200,
                    300,
                    400,
                    500
                ],

                "classifier__max_depth": [
                    3,
                    4,
                    5,
                    6
                ],

                "classifier__num_leaves": [
                    15,
                    20,
                    25,
                    31
                ],

                "classifier__learning_rate": [
                    0.02,
                    0.03,
                    0.05,
                    0.08
                ],

                "classifier__subsample": [
                    0.7,
                    0.8,
                    0.9,
                    1.0
                ],

                "classifier__colsample_bytree": [
                    0.7,
                    0.8,
                    0.9,
                    1.0
                ]
            }
        }
    }

    return model_configs


# ============================================================
# 3. HYPERPARAMETER TUNING, THRESHOLDING, AND EVALUATION
# ============================================================

def tune_model(
    model_name,
    pipeline,
    params,
    X_train,
    y_train
):
    """
    Tune one model using RandomizedSearchCV.

    ROC AUC is used as the main tuning metric because
    the target classes are imbalanced.
    """

    print()
    print("=" * 70)
    print(f"TUNING: {model_name}")
    print("=" * 70)

    cv = StratifiedKFold(
        n_splits=3,
        shuffle=True,
        random_state=RANDOM_STATE
    )

    # Randomized search tests a practical sample of parameter
    # combinations instead of trying every possible combination.
    search = RandomizedSearchCV(
        estimator=pipeline,
        param_distributions=params,
        n_iter=12,
        scoring="roc_auc",
        cv=cv,
        random_state=RANDOM_STATE,
        n_jobs=-1,
        verbose=1
    )

    search.fit(
        X_train,
        y_train
    )

    print()
    print("Best parameters:")

    for parameter, value in search.best_params_.items():
        print(parameter, "=", value)

    print()
    print(
        f"Best cross validation ROC AUC: "
        f"{search.best_score_:.4f}"
    )

    return search.best_estimator_


def find_best_threshold(
    model,
    X_train,
    y_train
):
    """
    Automatically find a classification threshold.

    Thresholds from 0.30 to 0.80 are tested using
    cross validated training probabilities.

    A minimum precision of 0.40 is required.
    Among valid thresholds, the threshold with the
    highest F1 score is selected.
    """

    cv = StratifiedKFold(
        n_splits=3,
        shuffle=True,
        random_state=RANDOM_STATE
    )

    # Cross-validated probabilities prevent the threshold from
    # being selected using predictions from the final test set.
    y_probability = cross_val_predict(
        model,
        X_train,
        y_train,
        cv=cv,
        method="predict_proba",
        n_jobs=-1
    )[:, 1]

    best_threshold = 0.50
    best_f1 = -1.0
    found_valid_threshold = False

    fallback_threshold = 0.50
    fallback_f1 = -1.0

    # Test thresholds from 0.30 through 0.80 in steps of 0.01.
    for threshold_value in range(30, 81):

        threshold = threshold_value / 100

        y_pred = (
            y_probability >= threshold
        ).astype(int)

        precision = precision_score(
            y_train,
            y_pred,
            zero_division=0
        )

        f1 = f1_score(
            y_train,
            y_pred,
            zero_division=0
        )

        # Keep a fallback based on the highest F1 score
        # in case no threshold reaches minimum precision.
        if f1 > fallback_f1:
            fallback_f1 = f1
            fallback_threshold = threshold

        # Main rule:
        # precision must be at least 0.40,
        # then select the highest F1 score.
        if (
            precision >= 0.40
            and f1 > best_f1
        ):
            best_f1 = f1
            best_threshold = threshold
            found_valid_threshold = True

    if not found_valid_threshold:
        best_threshold = fallback_threshold

    return best_threshold


def evaluate_model(
    model,
    X_test,
    y_test,
    threshold
):
    """
    Evaluate one trained model using its automatically
    selected classification threshold.
    """

    y_probability = model.predict_proba(
        X_test
    )[:, 1]

    y_pred = (
        y_probability >= threshold
    ).astype(int)

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

    return results, y_pred


# ============================================================
# 4. TRAIN, COMPARE, AND SELECT THE BEST MODEL
# ============================================================

def train_models(
    X_train,
    X_test,
    y_train,
    y_test
):
    """
    Tune, train, and compare all models.
    """

    scale_pos_weight = calculate_scale_pos_weight(
        y_train
    )

    print()
    print(
        f"XGBoost scale pos weight: "
        f"{scale_pos_weight:.4f}"
    )

    model_configs = create_model_configs(
        scale_pos_weight
    )

    results = []

    trained_models = {}

    best_model = None
    best_model_name = None
    best_model_threshold = 0.50
    best_roc_auc = 0

    # Repeat the same tuning and evaluation process for each
    # candidate model so their results can be compared fairly.
    for model_name, config in model_configs.items():

        # Step A: tune the model using only the training data.
        best_model_for_type = tune_model(
            model_name,
            config["pipeline"],
            config["params"],
            X_train,
            y_train
        )

        trained_models[
            model_name
        ] = best_model_for_type

        # Step B: choose a probability threshold for converting
        # probabilities into Yes/No predictions.
        best_threshold = find_best_threshold(
            best_model_for_type,
            X_train,
            y_train
        )

        print()
        print(
            f"Recommended threshold: "
            f"{best_threshold:.2f}"
        )

        # Step C: measure final performance on unseen test data.
        model_results, y_pred = evaluate_model(
            best_model_for_type,
            X_test,
            y_test,
            best_threshold
        )

        print()
        print(
            f"TEST RESULTS: {model_name}"
        )

        print()

        print(
            f"Accuracy:  "
            f"{model_results['Accuracy']:.4f}"
        )

        print(
            f"Precision: "
            f"{model_results['Precision']:.4f}"
        )

        print(
            f"Recall:    "
            f"{model_results['Recall']:.4f}"
        )

        print(
            f"F1 Score:  "
            f"{model_results['F1 Score']:.4f}"
        )

        print(
            f"ROC AUC:   "
            f"{model_results['ROC AUC']:.4f}"
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

        results.append(
            {
                "Model": model_name,
                "Threshold":
                    best_threshold,
                "Accuracy":
                    model_results["Accuracy"],
                "Precision":
                    model_results["Precision"],
                "Recall":
                    model_results["Recall"],
                "F1 Score":
                    model_results["F1 Score"],
                "ROC AUC":
                    model_results["ROC AUC"]
            }
        )

        # ROC AUC is the selection metric because it measures
        # ranking quality across thresholds on imbalanced data.
        if (
            model_results["ROC AUC"]
            > best_roc_auc
        ):

            best_roc_auc = (
                model_results["ROC AUC"]
            )

            best_model = (
                best_model_for_type
            )

            best_model_name = (
                model_name
            )

            best_model_threshold = (
                best_threshold
            )

    results_df = pd.DataFrame(
        results
    )

    results_df = results_df.sort_values(
        "ROC AUC",
        ascending=False
    ).reset_index(
        drop=True
    )

    return (
        best_model,
        best_model_name,
        best_model_threshold,
        results_df,
        trained_models
    )


# ============================================================
# 5. SAVE THE MODEL ARTIFACT USED BY THE INFERENCE API
# ============================================================

def save_model(
    model,
    model_name
):
    """
    Save the best trained model.
    """

    os.makedirs(
        MODEL_FOLDER,
        exist_ok=True
    )

    joblib.dump(
        model,
        MODEL_PATH
    )

    print()
    print("=" * 70)

    print(
        "MODEL SAVED SUCCESSFULLY"
    )

    print("=" * 70)

    print(
        f"Best model: {model_name}"
    )

    print(
        f"Saved to: {MODEL_PATH}"
    )


# ============================================================
# 6. RUN THE COMPLETE TRAINING WORKFLOW
# ============================================================

def main():

    print("=" * 70)

    print(
        "BANK TERM DEPOSIT MODEL TRAINING"
    )

    print("=" * 70)

    # Step 1: load the source CSV and apply data-cleaning rules.
    df = load_data()

    df = clean_data(
        df
    )

    # Step 2: separate the 15 model inputs from the target label.
    X, y = prepare_features(
        df
    )

    print()
    print("Dataset size:")
    print(
        df.shape
    )

    print()
    print("Target distribution:")
    print(
        y.value_counts()
    )

    print()
    print("Target percentage:")
    print(
        y.value_counts(
            normalize=True
        ) * 100
    )

    # Step 3: reserve 20% of the data for final testing.
    (
        X_train,
        X_test,
        y_train,
        y_test
    ) = split_dataset(
        X,
        y
    )

    print()
    print("Training rows:")
    print(
        len(X_train)
    )

    print()
    print("Testing rows:")
    print(
        len(X_test)
    )

    print()
    print(
        "Training target distribution:"
    )

    print(
        y_train.value_counts(
            normalize=True
        ) * 100
    )

    # Step 4: tune, evaluate, and compare all four models.
    (
        best_model,
        best_model_name,
        best_model_threshold,
        results_df,
        trained_models
    ) = train_models(
        X_train,
        X_test,
        y_train,
        y_test
    )

    print()
    print("=" * 70)

    print(
        "FINAL MODEL COMPARISON"
    )

    print("=" * 70)

    print()

    print(
        results_df.to_string(
            index=False
        )
    )

    print()
    print("=" * 70)

    print(
        "BEST MODEL"
    )

    print("=" * 70)

    print(
        best_model_name
    )

    print(
        f"ROC AUC: "
        f"{results_df.iloc[0]['ROC AUC']:.4f}"
    )

    print(
        f"Recommended threshold: "
        f"{best_model_threshold:.2f}"
    )

    print()
    print(
        "Copy this threshold into "
        "PREDICTION_THRESHOLD in config.py "
        "before running evaluate.py."
    )

    # Step 5: save the winning fitted pipeline as best_model.joblib.
    save_model(
        best_model,
        best_model_name
    )

    print()
    print(
        "Training completed successfully."
    )


if __name__ == "__main__":
    main()
