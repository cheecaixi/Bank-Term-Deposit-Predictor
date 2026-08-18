import time
from typing import Optional, Literal
from fastapi import FastAPI, HTTPException, status, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
import httpx

from app.config import settings

# Initialize FastAPI Application[cite: 8]
app = FastAPI(
    title="Bank Marketing API Gateway",
    description="Central API Gateway orchestrating Member A (AI Inference), Member C (Dashboard), and Member D (Database/Monitoring).",
    version="1.0.0"
)

# Enable CORS for Member C's Dashboard / Frontend[cite: 8]
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Load Microservice URLs from shared config[cite: 7, 8]
INFERENCE_URL = settings.INFERENCE_SERVICE_URL
DATABASE_URL = settings.DATABASE_SERVICE_URL
MONITORING_URL = settings.MONITORING_SERVICE_URL
TIMEOUT_SECONDS = settings.TIMEOUT_SECONDS


# ----------------------------------------------------
# CENTRALIZED MONITORING MIDDLEWARE[cite: 8]
# ----------------------------------------------------
@app.middleware("http")
async def log_requests_to_monitoring(request: Request, call_next):
    start_time = time.time()
    
    response = await call_next(request)
    
    process_time_seconds = time.time() - start_time
    
    # Filter out noisy root and health check logs
    if request.url.path not in ["/health", "/"]:
        log_payload = {
            "endpoint": request.url.path,
            "method": request.method,
            "status_code": response.status_code,
            "execution_time_seconds": round(process_time_seconds, 4)
        }
        
        try:
            async with httpx.AsyncClient() as client:
                await client.post(
                    f"{MONITORING_URL}/logs",
                    json=log_payload,
                    timeout=1.0
                )
        except Exception:
            # Prevent monitoring connection drops from failing core gateway execution[cite: 8]
            pass

    return response


# ----------------------------------------------------
# PYDANTIC SCHEMAS FOR DATA VALIDATION[cite: 8]
# ----------------------------------------------------
class CustomerPredictModel(BaseModel):
    phone_number: str = Field(..., pattern=r"^\d{8}$", example="91234567")
    age: int = Field(..., example=35)
    job: Literal[
        "admin.", "blue-collar", "entrepreneur", "housemaid",
        "management", "retired", "self-employed", "services",
        "student", "technician", "unemployed", "unknown"
    ] = Field(..., example="management")
    marital: Literal["married", "single", "divorced"] = Field(..., example="married")
    education: Literal["primary", "secondary", "tertiary", "unknown"] = Field(..., example="tertiary")
    default: Literal["yes", "no"] = Field(..., example="no")
    balance: float = Field(..., example=1500)
    housing: Literal["yes", "no"] = Field(..., example="yes")
    loan: Literal["yes", "no"] = Field(..., example="no")
    contact: Literal["cellular", "telephone", "unknown"] = Field(..., example="cellular")
    day: int = Field(..., example=15)
    month: Literal[
        "jan", "feb", "mar", "apr", "may", "jun",
        "jul", "aug", "sep", "oct", "nov", "dec"
    ] = Field(..., example="may")
    campaign: int = Field(..., example=1)
    pdays: int = Field(..., example=-1)
    previous: int = Field(..., example=0)
    poutcome: Literal["failure", "other", "success", "unknown"] = Field(..., example="unknown")
    batch_id: Optional[int] = Field(None, gt=0, example=1)

class BatchUploadModel(BaseModel):
    file_name: str = Field(..., example="bank_customers_august.csv")
    total_records: int = Field(..., gt=0, example=50)

class CustomerUpdateModel(BaseModel):
    phone_number: Optional[str] = Field(None, pattern=r"^\d{8}$", example="91234567")
    age: Optional[int] = Field(None, example=36)
    job: Optional[Literal[
        "admin.", "blue-collar", "entrepreneur", "housemaid",
        "management", "retired", "self-employed", "services",
        "student", "technician", "unemployed", "unknown"
    ]] = Field(None, example="technician")
    marital: Optional[Literal["married", "single", "divorced"]] = Field(None, example="single")
    education: Optional[Literal["primary", "secondary", "tertiary", "unknown"]] = Field(None, example="tertiary")
    default: Optional[Literal["yes", "no"]] = Field(None, example="no")
    balance: Optional[float] = Field(None, example=2000)
    housing: Optional[Literal["yes", "no"]] = Field(None, example="yes")
    loan: Optional[Literal["yes", "no"]] = Field(None, example="no")
    batch_id: Optional[int] = Field(None, gt=0, example=1)


# ----------------------------------------------------
# 1. HEALTH & ROOT ENDPOINTS[cite: 8]
# ----------------------------------------------------
@app.get("/", tags=["Health"])
def read_root():
    return {
        "message": "Bank Marketing API Gateway is running!",
        "docs": "Visit /docs for interactive Swagger UI documentation."
    }

@app.get("/health", tags=["Health"])
def health_check():
    return {"status": "healthy", "service": "api-gateway"}


# ----------------------------------------------------
# 2. PREDICT ENDPOINT (FORWARD TO MEMBER A & PERSIST TO MEMBER D)[cite: 8]
# ----------------------------------------------------
@app.post("/api/predict", tags=["Predictions"])
async def predict_subscription(customer_data: CustomerPredictModel):
    async with httpx.AsyncClient() as client:
        payload = customer_data.model_dump()
        
        # Exclude non-inference fields (phone_number and batch_id)[cite: 8]
        inference_payload = {
            field: value
            for field, value in payload.items()
            if field not in ("phone_number", "batch_id")
        }

        # Step A: Request prediction from Member A (AI Inference)[cite: 8]
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
                status_code=exc.response.status_code,
                detail=f"Member A (AI Inference Service) error: {exc.response.text}"
            )
        except httpx.RequestError as exc:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=f"Member A (AI Inference Service) unreachable: {exc}"
            )

        # Step B: Persist customer, campaign, and prediction data to Member D[cite: 8]
        try:
            customer_payload = {
                field: payload[field]
                for field in (
                    "phone_number", "age", "job", "marital", "education",
                    "default", "balance", "housing", "loan", "batch_id"
                )
                if field in payload and payload[field] is not None
            }

            customer_response = await client.post(
                f"{DATABASE_URL}/customers",
                json=customer_payload,
                timeout=TIMEOUT_SECONDS
            )

            if customer_response.status_code == 409:
                customers_response = await client.get(
                    f"{DATABASE_URL}/customers",
                    timeout=TIMEOUT_SECONDS
                )
                customers_response.raise_for_status()
                customer = next(
                    (
                        item for item in customers_response.json()
                        if item.get("phone_number") == payload["phone_number"]
                    ),
                    None
                )
                if customer is None:
                    raise HTTPException(
                        status_code=409,
                        detail="Customer exists but could not be retrieved"
                    )
                customer_id = customer["customer_id"]

                # Forward updated demographic data and batch_id to Member D[cite: 8, 29]
                await client.put(
                    f"{DATABASE_URL}/customers/{customer_id}",
                    json=customer_payload,
                    timeout=TIMEOUT_SECONDS
                )
            else:
                customer_response.raise_for_status()
                customer_id = customer_response.json()["customer_id"]

            campaign_response = await client.post(
                f"{DATABASE_URL}/campaign-history",
                json={
                    "customer_id": customer_id,
                    "contact": payload["contact"],
                    "day": payload["day"],
                    "month": payload["month"],
                    "campaign": payload["campaign"],
                    "pdays": payload["pdays"],
                    "previous": payload["previous"],
                    "poutcome": payload["poutcome"]
                },
                timeout=TIMEOUT_SECONDS
            )
            campaign_response.raise_for_status()

            prediction_response = await client.post(
                f"{DATABASE_URL}/predictions",
                json={
                    "customer_id": customer_id,
                    "prediction": prediction_result["subscription"],
                    "probability": prediction_result["probability"]
                },
                timeout=TIMEOUT_SECONDS
            )
            prediction_response.raise_for_status()

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

        return prediction_result


# ----------------------------------------------------
# 3. BATCH UPLOADS ENDPOINTS (FORWARD TO MEMBER D)[cite: 29]
# ----------------------------------------------------
@app.post("/api/batch-uploads", tags=["Batch Uploads"])
async def create_batch_upload(batch: BatchUploadModel):
    """
    Register a new batch upload record in Member D.[cite: 29]
    """
    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(
                f"{DATABASE_URL}/batch-uploads",
                json=batch.model_dump(),
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


@app.get("/api/batch-uploads/{batch_id}/customers", tags=["Batch Uploads"])
async def get_customers_by_batch(batch_id: int):
    """
    Fetch all customer records associated with a specific batch ID from Member D.[cite: 29]
    """
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(
                f"{DATABASE_URL}/batch-uploads/{batch_id}/customers",
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


@app.get("/api/batch-uploads/{batch_id}/results", tags=["Batch Uploads"])
async def get_results_by_batch(batch_id: int):
    """
    Fetch joined customer and prediction results for a specific batch ID from Member D.[cite: 29]
    """
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(
                f"{DATABASE_URL}/batch-uploads/{batch_id}/results",
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
# 4. GET HISTORICAL RECORDS (FORWARD TO MEMBER D)[cite: 8]
# ----------------------------------------------------
@app.get("/api/results", tags=["Analytics"])
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
# 5. SEARCH CUSTOMER BY PHONE NUMBER[cite: 8]
# ----------------------------------------------------
@app.get("/api/customers/phone/{phone_number}", tags=["Customers"])
async def get_customer_by_phone(phone_number: str):
    """
    Search for an existing customer by phone number.[cite: 8]
    """
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(
                f"{DATABASE_URL}/customers",
                timeout=TIMEOUT_SECONDS
            )

            response.raise_for_status()
            customers = response.json()

            customer = next(
                (
                    item
                    for item in customers
                    if str(item.get("phone_number", "")).strip() == phone_number.strip()
                ),
                None
            )

            if customer is None:
                raise HTTPException(
                    status_code=404,
                    detail="Customer not found"
                )

            return customer

        except HTTPException:
            raise

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
# 6. UPDATE CUSTOMER RECORD (PUT -> MEMBER D)[cite: 8]
# ----------------------------------------------------
@app.put("/api/customers/{customer_id}", tags=["Customers"])
async def update_customer(
    customer_id: int,
    updated_data: CustomerUpdateModel
):
    """
    Receives updated customer records from Member C (Dashboard)
    and forwards the PUT request to Member D (Database Service).[cite: 8]
    """
    async with httpx.AsyncClient() as client:
        try:
            payload = updated_data.model_dump(
                exclude_unset=True
            )

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
# 7. DELETE CUSTOMER RECORD (DELETE -> MEMBER D)[cite: 8]
# ----------------------------------------------------
@app.delete("/api/customers/{customer_id}", tags=["Customers"])
async def delete_customer(customer_id: int):
    """
    Receives a customer deletion request from Member C (Dashboard)
    and forwards the DELETE request to Member D (Database Service).[cite: 8]
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
# 8. MONITORING ENDPOINTS (FORWARD TO MEMBER D MONITORING)[cite: 8]
# ----------------------------------------------------
@app.get("/api/logs", tags=["Monitoring"], summary="Get detailed log history")
async def fetch_system_logs():
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(
                f"{MONITORING_URL}/logs",
                timeout=TIMEOUT_SECONDS
            )
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as exc:
            raise HTTPException(
                status_code=exc.response.status_code,
                detail=f"Monitoring Service error: {exc.response.text}"
            )
        except httpx.RequestError as exc:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=f"Monitoring Service unreachable: {exc}"
            )


@app.get(
    "/api/monitoring/status",
    tags=["Monitoring"],
    summary="Get current health of all microservices"
)
async def fetch_monitoring_status():
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(
                f"{MONITORING_URL}/status",
                timeout=TIMEOUT_SECONDS
            )
            response.raise_for_status()
            return response.json()

        except httpx.HTTPStatusError as exc:
            raise HTTPException(
                status_code=exc.response.status_code,
                detail=f"Monitoring Service error: {exc.response.text}"
            )

        except httpx.RequestError as exc:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=f"Monitoring Service unreachable: {exc}"
            )


@app.get(
    "/api/monitoring/metrics",
    tags=["Monitoring"],
    summary="Get aggregated monitoring metrics"
)
async def fetch_monitoring_metrics():
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(
                f"{MONITORING_URL}/metrics",
                timeout=TIMEOUT_SECONDS
            )
            response.raise_for_status()
            return response.json()

        except httpx.HTTPStatusError as exc:
            raise HTTPException(
                status_code=exc.response.status_code,
                detail=f"Monitoring Service error: {exc.response.text}"
            )

        except httpx.RequestError as exc:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=f"Monitoring Service unreachable: {exc}"
            )