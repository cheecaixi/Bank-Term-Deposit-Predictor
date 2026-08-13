import os
from typing import Optional, Dict, Any
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
DATABASE_URL = os.getenv("DATABASE_SERVICE_URL", "http://localhost:7001")
MONITORING_URL = os.getenv("MONITORING_SERVICE_URL", "http://localhost:7002")
TIMEOUT_SECONDS = float(os.getenv("TIMEOUT_SECONDS", 5.0))


# ----------------------------------------------------
# PYDANTIC SCHEMAS FOR DATA VALIDATION
# ----------------------------------------------------
class CustomerPredictModel(BaseModel):
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
    age: Optional[int] = Field(None, example=36)
    job: Optional[str] = Field(None, example="technician")
    marital: Optional[str] = Field(None, example="single")
    education: Optional[str] = Field(None, example="tertiary")
    balance: Optional[int] = Field(None, example=2000)
    duration: Optional[int] = Field(None, example=150)


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
    """
    Receives customer features from Member C (Dashboard),
    forwards to Member A (AI Inference Service),
    and asynchronously persists the result to Member D (Database Service).
    """
    async with httpx.AsyncClient() as client:
        payload = customer_data.dict()

        # Step A: Request prediction from Member A (AI Inference)
        try:
            inference_response = await client.post(
                f"{INFERENCE_URL}/predict",
                json=payload,
                timeout=TIMEOUT_SECONDS
            )
            inference_response.raise_for_status()
            prediction_result = inference_response.json()
        except httpx.RequestError as exc:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=f"Member A (AI Inference Service) unreachable: {exc}"
            )

        # Step B: Persist prediction log to Member D (Database Service)
        try:
            db_payload = {
                "customer_input": payload,
                "prediction": prediction_result.get("prediction"),
                "probability": prediction_result.get("probability")
            }
            await client.post(
                f"{DATABASE_URL}/records",
                json=db_payload,
                timeout=3.0
            )
        except httpx.RequestError:
            # Non-blocking warning log if DB persistence fails
            print("Warning: Failed to persist record to Member D Database Service")

        # Step C: Return result to Member C (Dashboard)
        return prediction_result


# ----------------------------------------------------
# 3. GET HISTORICAL RECORDS (FORWARD TO MEMBER D)
# ----------------------------------------------------
@app.get("/api/results")
async def fetch_historical_results():
    """
    Fetches all historical prediction records from Member D (Database Service).
    """
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(
                f"{DATABASE_URL}/records",
                timeout=TIMEOUT_SECONDS
            )
            response.raise_for_status()
            return response.json()
        except httpx.RequestError as exc:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=f"Member D (Database Service) unreachable: {exc}"
            )


# ----------------------------------------------------
# 4. UPDATE CUSTOMER RECORD (PUT -> MEMBER D)
# ----------------------------------------------------
@app.put("/api/customers/{customer_id}")
async def update_customer(customer_id: str, updated_data: CustomerUpdateModel):
    """
    Receives updated customer records from Member C (Dashboard)
    and forwards the PUT request to Member D (Database Service).
    """
    async with httpx.AsyncClient() as client:
        try:
            payload = updated_data.dict(exclude_unset=True)
            response = await client.put(
                f"{DATABASE_URL}/records/{customer_id}",
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
async def delete_customer(customer_id: str):
    """
    Receives a customer deletion request from Member C (Dashboard)
    and forwards the DELETE request to Member D (Database Service).
    """
    async with httpx.AsyncClient() as client:
        try:
            response = await client.delete(
                f"{DATABASE_URL}/records/{customer_id}",
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
    """
    Fetches system latency and request logs from Member D (Monitoring Service).
    """
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