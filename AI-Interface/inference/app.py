# app.py
# FastAPI AI inference service for bank term deposit prediction

import time
import joblib
import pandas as pd

from fastapi import FastAPI, HTTPException

from config import (
    MODEL_PATH,
    PREDICTION_THRESHOLD,
    MODEL_NAME,
    MODEL_VERSION,
    NUMBER_OF_FEATURES
)

from inference.schemas import CustomerData


# Create FastAPI application
app = FastAPI(
    title="Bank Term Deposit AI Inference Service",
    description=(
        "Predict whether a customer is likely "
        "to subscribe to a term deposit"
    ),
    version=MODEL_VERSION
)


# Load the trained model when the API starts
try:

    model = joblib.load(
        MODEL_PATH
    )

    model_loaded = True

    # Work out which column of predict_proba() corresponds
    # to the positive class (target = 1, "subscribed").
    #
    # This does NOT assume the positive class is always at
    # index 1 -- it looks it up from the model itself, so it
    # stays correct even if classes_ is ordered differently.
    POSITIVE_CLASS_INDEX = list(
        model.classes_
    ).index(1)

    print("Model loaded successfully")
    print(MODEL_PATH)
    print("Model classes:", model.classes_)
    print("Positive class index:", POSITIVE_CLASS_INDEX)

except Exception as error:

    model = None

    model_loaded = False

    POSITIVE_CLASS_INDEX = None

    print("Model could not be loaded")
    print(error)


@app.get("/")
def root():
    """
    Confirm that the AI inference service is running.
    """

    return {
        "service": "ai-inference",
        "status": "running"
    }


@app.get("/health")
def health():
    """
    Check whether the API and model are available.
    """

    if model_loaded:

        return {
            "status": "healthy",
            "service": "ai-inference",
            "model_loaded": True
        }

    return {
        "status": "unhealthy",
        "service": "ai-inference",
        "model_loaded": False
    }


@app.get("/model-info")
def model_info():
    """
    Return information about the deployed model.
    """

    return {
        "model_name": MODEL_NAME,
        "model_version": MODEL_VERSION,
        "model_loaded": model_loaded,
        "prediction_threshold": PREDICTION_THRESHOLD,
        "number_of_features": NUMBER_OF_FEATURES
    }


@app.post("/predict")
def predict(customer: CustomerData):
    """
    Predict whether a customer is likely
    to subscribe to a term deposit.
    """

    # Make sure the model is available
    if model is None:

        raise HTTPException(
            status_code=503,
            detail="Prediction model is unavailable"
        )

    try:

        start_time = time.time()

        # Convert incoming customer data into dictionary
        customer_data = customer.model_dump()

        # Convert dictionary into DataFrame
        customer_df = pd.DataFrame(
            [customer_data]
        )

        # Predict probability of subscription.
        #
        # POSITIVE_CLASS_INDEX is looked up once at startup
        # from model.classes_, instead of assuming the
        # positive class is always in column [1]. This avoids
        # silently inverted predictions if the model's class
        # ordering ever changes.
        probability = model.predict_proba(
            customer_df
        )[0][POSITIVE_CLASS_INDEX]

        # Apply the selected probability threshold
        prediction = int(
            probability >= PREDICTION_THRESHOLD
        )

        # Convert prediction into readable result
        if prediction == 1:
            subscription = "Yes"
        else:
            subscription = "No"

        # Calculate prediction processing time
        processing_time = (
            time.time() - start_time
        )

        return {
            "prediction": prediction,
            "subscription": subscription,
            "probability": round(
                float(probability),
                4
            ),
            "processing_time_seconds": round(
                processing_time,
                4
            )
        }

    except Exception as error:

        raise HTTPException(
            status_code=500,
            detail=str(error)
        )