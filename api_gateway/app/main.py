import os
from typing import Optional
from fastapi import FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
import httpx

# Initialize FastAPI Application
app = FastAPI(
    title="Bank Marketing API Gateway",
    description="Central API Gateway orchestrating Member A (AI Inference), Member C (Dashboard), and Member D (Database/Monitoring).",
    version="1.0.0"
)

# Enable CORS for Member C's Dashboard / Frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Load Microservice URLs from Environment Variables (With Local Development Fallbacks)
INFERENCE_URL = os.getenv("INFERENCE_SERVICE_URL", "http://localhost:7000")
DATABASE_URL = os.getenv("DATABASE_SERVICE_URL", "http://localhost:8000")
MONITORING_URL = os.getenv("MONITORING_SERVICE_URL", "http://localhost:7002")
TIMEOUT_SECONDS = float(os.getenv("TIMEOUT_SECONDS", 5.0))


# ----------------------------------------------------
# PYDANTIC SCHEMAS FOR DATA VALIDATION
# ----------------------------------------------------
class CustomerPredictModel(BaseModel):
    phone_number: str = Field(..., example="91234567")
    age: int = Field(..., example=35)
    job: str = Field(..., example="management")
    marital: str = Field(..., example="married")
    education: str = Field(..., example="tertiary")
    default: str = Field(..., example="no")
    balance: float = Field(..., example=1500)
    housing: str = Field(..., example="yes")
    loan: str = Field(..., example="no")
    contact: str = Field(..., example="cellular")
    day: int = Field(..., example=15)
    month: str = Field(..., example="may")
    campaign: int = Field(..., example=1)
    pdays: int = Field(..., example=-1)
    previous: int = Field(..., example=0)
    poutcome: str = Field(..., example="unknown")

class CustomerUpdateModel(BaseModel):
    phone_number: Optional[str] = Field(None, example="91234567")
    age: Optional[int] = Field(None, example=36)
    job: Optional[str] = Field(None, example="technician")
    marital: Optional[str] = Field(None, example="single")
    education: Optional[str] = Field(None, example="tertiary")
    default: Optional[str] = Field(None, example="no")
    balance: Optional[float] = Field(None, example=2000)
    housing: Optional[str] = Field(None, example="yes")
    loan: Optional[str] = Field(None, example="no")


# ----------------------------------------------------
# 1. HEALTH & ROOT ENDPOINTS
# ----------------------------------------------------
@app.get("/")
def read_root():
    return {
        "message": "Bank Marketing API Gateway is running!",
        "docs": "Visit /docs for interactive Swagger UI documentation."
    }

@app.get("/health")
def health_check():
    return {"status": "healthy", "service": "api-gateway"}


# ----------------------------------------------------
# 2. PREDICT ENDPOINT (FORWARD TO MEMBER A & PERSIST TO MEMBER D)
# ----------------------------------------------------
@app.post("/api/predict")
async def predict_subscription(customer_data: CustomerPredictModel):

    payload = customer_data.model_dump()

    # =========================================================
    # STEP 1 — SEND ONLY MODEL FEATURES TO MEMBER A
    # =========================================================

    inference_payload = {
        field: value
        for field, value in payload.items()
        if field != "phone_number"
    }

    async with httpx.AsyncClient() as client:

        try:
            inference_response = await client.post(
                f"{INFERENCE_URL}/predict",
                json=inference_payload,
                timeout=TIMEOUT_SECONDS
            )

            inference_response.raise_for_status()

            prediction_result = inference_response.json()

        except httpx.HTTPStatusError as exc:
            raise HTTPException(
                status_code=502,
                detail=(
                    "Member A prediction failed: "
                    f"{exc.response.text}"
                )
            )

        except httpx.RequestError as exc:
            raise HTTPException(
                status_code=503,
                detail=(
                    "Member A is unreachable: "
                    f"{exc}"
                )
            )

        # =========================================================
        # STEP 2 — CREATE OR FIND CUSTOMER IN MEMBER D
        # =========================================================

        customer_payload = {
            "phone_number": payload["phone_number"],
            "age": payload["age"],
            "job": payload["job"],
            "marital": payload["marital"],
            "education": payload["education"],
            "default": payload["default"],
            "balance": payload["balance"],
            "housing": payload["housing"],
            "loan": payload["loan"]
        }

        try:

            customer_response = await client.post(
                f"{DATABASE_URL}/customers",
                json=customer_payload,
                timeout=TIMEOUT_SECONDS
            )

            # New customer
            if customer_response.status_code == 201:
                customer = customer_response.json()
                customer_id = customer["customer_id"]

            # Existing customer
            elif customer_response.status_code == 409:

                customers_response = await client.get(
                    f"{DATABASE_URL}/customers",
                    timeout=TIMEOUT_SECONDS
                )

                customers_response.raise_for_status()

                customers = customers_response.json()

                customer = next(
                    (
                        item
                        for item in customers
                        if item.get("phone_number")
                        == payload["phone_number"]
                    ),
                    None
                )

                if customer is None:
                    raise HTTPException(
                        status_code=404,
                        detail=(
                            "Customer already exists, "
                            "but could not be retrieved."
                        )
                    )

                customer_id = customer["customer_id"]

            else:

                customer_response.raise_for_status()

        except HTTPException:
            raise

        except httpx.HTTPStatusError as exc:
            raise HTTPException(
                status_code=502,
                detail=(
                    "Member D customer operation failed: "
                    f"{exc.response.text}"
                )
            )

        except httpx.RequestError as exc:
            raise HTTPException(
                status_code=503,
                detail=(
                    "Member D is unreachable: "
                    f"{exc}"
                )
            )

        # =========================================================
        # STEP 3 — SAVE CAMPAIGN HISTORY
        # =========================================================

        campaign_payload = {
            "customer_id": customer_id,
            "contact": payload["contact"],
            "day": payload["day"],
            "month": payload["month"],
            "campaign": payload["campaign"],
            "pdays": payload["pdays"],
            "previous": payload["previous"],
            "poutcome": payload["poutcome"]
        }

        try:

            campaign_response = await client.post(
                f"{DATABASE_URL}/campaign-history",
                json=campaign_payload,
                timeout=TIMEOUT_SECONDS
            )

            campaign_response.raise_for_status()

        except httpx.HTTPStatusError as exc:
            raise HTTPException(
                status_code=502,
                detail=(
                    "Failed to save campaign history to Member D: "
                    f"{exc.response.text}"
                )
            )

        except httpx.RequestError as exc:
            raise HTTPException(
                status_code=503,
                detail=(
                    "Member D campaign-history endpoint is unreachable: "
                    f"{exc}"
                )
            )

        # =========================================================
        # STEP 4 — SAVE PREDICTION
        # =========================================================

        prediction_payload = {
            "customer_id": customer_id,
            "prediction": prediction_result["subscription"],
            "probability": prediction_result["probability"]
        }

        try:

            prediction_response = await client.post(
                f"{DATABASE_URL}/predictions",
                json=prediction_payload,
                timeout=TIMEOUT_SECONDS
            )

            prediction_response.raise_for_status()

        except httpx.HTTPStatusError as exc:
            raise HTTPException(
                status_code=502,
                detail=(
                    "Failed to save prediction to Member D: "
                    f"{exc.response.text}"
                )
            )

        except httpx.RequestError as exc:
            raise HTTPException(
                status_code=503,
                detail=(
                    "Member D prediction endpoint is unreachable: "
                    f"{exc}"
                )
            )

        # =========================================================
        # STEP 5 — RETURN RESULT TO MEMBER C
        # =========================================================

        return {
            "customer_id": customer_id,
            "prediction": prediction_result["prediction"],
            "subscription": prediction_result["subscription"],
            "probability": prediction_result["probability"],
            "processing_time_seconds":
                prediction_result.get(
                    "processing_time_seconds"
                )
        }


# ----------------------------------------------------
# 3. GET HISTORICAL RECORDS (FORWARD TO MEMBER D)
# ----------------------------------------------------
@app.get("/api/results")
async def fetch_historical_results():
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(
                f"{DATABASE_URL}/predictions",
                timeout=TIMEOUT_SECONDS
            )
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as exc:
            raise HTTPException(
                status_code=exc.response.status_code,
                detail=f"Member D (Database Service) error: {exc.response.text}"
            )
        except httpx.RequestError as exc:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=f"Member D (Database Service) unreachable: {exc}"
            )


# ----------------------------------------------------
# 4. UPDATE CUSTOMER RECORD (PUT -> MEMBER D)
# ----------------------------------------------------
@app.put("/api/customers/{customer_id}")
async def update_customer(customer_id: int, updated_data: CustomerUpdateModel):
    """
    Receives updated customer records from Member C (Dashboard)
    and forwards the PUT request to Member D (Database Service).
    """
    async with httpx.AsyncClient() as client:
        try:
            payload = updated_data.model_dump(exclude_unset=True)
            response = await client.put(
                f"{DATABASE_URL}/customers/{customer_id}",
                json=payload,
                timeout=TIMEOUT_SECONDS
            )
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as exc:
            raise HTTPException(
                status_code=exc.response.status_code,
                detail=f"Database Service error: {exc.response.text}"
            )
        except httpx.RequestError as exc:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=f"Member D (Database Service) unreachable: {exc}"
            )


# ----------------------------------------------------
# 5. DELETE CUSTOMER RECORD (DELETE -> MEMBER D)
# ----------------------------------------------------
@app.delete("/api/customers/{customer_id}")
async def delete_customer(customer_id: int):
    """
    Receives a customer deletion request from Member C (Dashboard)
    and forwards the DELETE request to Member D (Database Service).
    """
    async with httpx.AsyncClient() as client:
        try:
            response = await client.delete(
                f"{DATABASE_URL}/customers/{customer_id}",
                timeout=TIMEOUT_SECONDS
            )
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as exc:
            raise HTTPException(
                status_code=exc.response.status_code,
                detail=f"Database Service error: {exc.response.text}"
            )
        except httpx.RequestError as exc:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=f"Member D (Database Service) unreachable: {exc}"
            )


# ----------------------------------------------------
# 6. GET SYSTEM LOGS (FORWARD TO MEMBER D MONITORING)
# ----------------------------------------------------
@app.get("/api/logs")
async def fetch_system_logs():
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(
                f"{MONITORING_URL}/logs",
                timeout=TIMEOUT_SECONDS
            )
            response.raise_for_status()
            return response.json()
        except httpx.RequestError as exc:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=f"Member D (Monitoring Service) unreachable: {exc}"
            )