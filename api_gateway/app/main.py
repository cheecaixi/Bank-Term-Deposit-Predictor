import os
import httpx
from fastapi import FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

app = FastAPI(title="Bank Marketing API Gateway", version="1.0.0")

# Enable CORS so Member C (Dashboard) can send requests from browser/Streamlit
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Service URLs loaded from environment variables (configured via config.py / k8s)
INFERENCE_URL = os.getenv("INFERENCE_SERVICE_URL", "http://ai-inference-service:7000")
DATABASE_URL = os.getenv("DATABASE_SERVICE_URL", "http://database-service:7001")
MONITORING_URL = os.getenv("MONITORING_SERVICE_URL", "http://monitoring-service:7002")


# ----------------------------------------------------
# 1. CONNECTING TO MEMBER A (AI Inference Service)
# ----------------------------------------------------
@app.post("/api/predict")
async def predict_subscription(customer_data: dict):
    """
    Receives customer payload from Member C (Dashboard),
    forwards to Member A (AI Inference),
    and saves result to Member D (Database).
    """
    async with httpx.AsyncClient() as client:
        # Step A: Request prediction from Member A
        try:
            inference_response = await client.post(
                f"{INFERENCE_URL}/predict",
                json=customer_data,
                timeout=5.0
            )
            inference_response.raise_for_status()
            prediction_result = inference_response.json()
        except httpx.RequestError as exc:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=f"Member A (AI Inference) service unreachable: {exc}"
            )

        # Step B: Asynchronously save prediction to Member D (Database)
        try:
            db_payload = {
                "customer_input": customer_data,
                "prediction": prediction_result.get("prediction"),
                "probability": prediction_result.get("probability")
            }
            await client.post(f"{DATABASE_URL}/records", json=db_payload, timeout=3.0)
        except httpx.RequestError:
            # Non-blocking log if DB call fails
            print("Warning: Failed to persist record to Database Service")

        # Step C: Return result back to Member C (Dashboard)
        return prediction_result


# ----------------------------------------------------
# 2. CONNECTING TO MEMBER D (Database Service)
# ----------------------------------------------------
@app.get("/api/results")
async def fetch_historical_results():
    """
    Fetches past predictions from Member D's database for the Dashboard analytics tab.
    """
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(f"{DATABASE_URL}/records", timeout=5.0)
            response.raise_for_status()
            return response.json()
        except httpx.RequestError:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Member D (Database Service) unreachable"
            )


# ----------------------------------------------------
# 3. CONNECTING TO MEMBER D (Monitoring Service)
# ----------------------------------------------------
@app.get("/api/logs")
async def fetch_system_logs():
    """
    Fetches operational metrics and error logs from Member D's Monitoring service.
    """
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(f"{MONITORING_URL}/logs", timeout=5.0)
            response.raise_for_status()
            return response.json()
        except httpx.RequestError:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Member D (Monitoring Service) unreachable"
            )