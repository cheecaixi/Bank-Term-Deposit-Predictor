# train.py
# Train, tune, compare, and save machine learning models
# for bank term deposit prediction

import os
import joblib
import pandas as pd

from sklearn.model_selection import (
    train_test_split,
    RandomizedSearchCV,
    StratifiedKFold
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

from cleaning import load_data, clean_data
from features import prepare_features, build_preprocessor


from config import (
    RANDOM_STATE,
    MODEL_PATH,
    AI_INTERFACE_DIR
)

MODEL_FOLDER = os.path.join(
    AI_INTERFACE_DIR,
    "models"
)

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


def create_model_configs(scale_pos_weight):
    """
    Create each model together with its tuning parameters.

    Different imbalance handling methods are used because
    each algorithm responds differently to imbalance.

    Random Forest, XGBoost, and LightGBM all support native
    class weighting, so they use class_weight / scale_pos_weight
    directly. GradientBoostingClassifier has no native class
    weighting option, so SMOTE oversampling is used instead for
    that model specifically.
    """

    model_configs = {

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

    Returns both the best fitted estimator and its
    cross-validation ROC AUC score. The CV score is what
    should be used to compare models against each other,
    since it is computed without ever touching the test set.
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

    return search.best_estimator_, search.best_score_


def evaluate_model(
    model,
    X_test,
    y_test
):
    """
    Evaluate one trained model on the held-out test set,
    using the default classification threshold of 0.50.

    This is used for FINAL REPORTING only. It must never be
    used to decide which model "wins" -- doing so would leak
    information from the test set into model selection, which
    would make the reported final ROC AUC optimistic.
    """

    y_pred = model.predict(
        X_test
    )

    y_probability = model.predict_proba(
        X_test
    )[:, 1]

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


def train_models(
    X_train,
    X_test,
    y_train,
    y_test
):
    """
    Tune, train, and compare all models.

    Model selection (deciding which model is "best") is based
    on cross-validation ROC AUC, computed entirely on the
    training set. The test set is only used afterwards, to
    report an honest, unbiased performance estimate for each
    model -- it never influences which model is chosen.
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
    best_cv_roc_auc = 0

    for model_name, config in model_configs.items():

        best_model_for_type, cv_roc_auc = tune_model(
            model_name,
            config["pipeline"],
            config["params"],
            X_train,
            y_train
        )

        trained_models[
            model_name
        ] = best_model_for_type

        model_results, y_pred = evaluate_model(
            best_model_for_type,
            X_test,
            y_test
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

        print(
            f"CV ROC AUC (used for selection): "
            f"{cv_roc_auc:.4f}"
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
                "CV ROC AUC":
                    cv_roc_auc,
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

        # Selection uses the cross-validation score, NOT the
        # test-set score. This keeps the test set completely
        # unseen until final reporting.
        if (
            cv_roc_auc
            > best_cv_roc_auc
        ):

            best_cv_roc_auc = (
                cv_roc_auc
            )

            best_model = (
                best_model_for_type
            )

            best_model_name = (
                model_name
            )

    results_df = pd.DataFrame(
        results
    )

    # Sorted by CV ROC AUC since that is the metric that
    # actually decided the winner. Test ROC AUC is included
    # alongside it for transparency, but is reporting-only.
    results_df = results_df.sort_values(
        "CV ROC AUC",
        ascending=False
    ).reset_index(
        drop=True
    )

    return (
        best_model,
        best_model_name,
        results_df,
        trained_models
    )


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


def main():

    print("=" * 70)

    print(
        "BANK TERM DEPOSIT MODEL TRAINING"
    )

    print("=" * 70)

    df = load_data()

    df = clean_data(
        df
    )

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

    (
        best_model,
        best_model_name,
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
        f"Selected by CV ROC AUC: "
        f"{results_df.iloc[0]['CV ROC AUC']:.4f}"
    )

    print(
        f"Test set ROC AUC (unbiased estimate): "
        f"{results_df.iloc[0]['ROC AUC']:.4f}"
    )

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