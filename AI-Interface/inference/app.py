# app.py
# FastAPI AI inference service for bank term deposit prediction
#
# Runtime flow:
# 1. Load the saved preprocessing-and-model pipeline at startup.
# 2. Validate incoming customer data with the Pydantic schema.
# 3. Return a prediction, probability, and processing time.

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


# ============================================================
# 1. CREATE THE FASTAPI APPLICATION
# ============================================================

# Create FastAPI application
app = FastAPI(
    title="Bank Term Deposit AI Inference Service",
    description=(
        "Predict whether a customer is likely "
        "to subscribe to a term deposit"
    ),
    version=MODEL_VERSION
)


# ============================================================
# 2. LOAD THE TRAINED MODEL WHEN THE SERVICE STARTS
# ============================================================

# Loading once at startup avoids reloading the model for every request.
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


# ============================================================
# 3. SERVICE INFORMATION AND HEALTH ENDPOINTS
# ============================================================

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

    raise HTTPException(
        status_code=503,
        detail="Prediction model is unavailable"
    )


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


# ============================================================
# 4. REAL-TIME PREDICTION ENDPOINT
# ============================================================

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

        # The saved pipeline expects one row with the original
        # feature names, so the request becomes a DataFrame.
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
        # The saved pipeline first preprocesses the row and then
        # asks the selected classifier for class probabilities.
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

        # Return a small JSON response for the API Gateway.
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
