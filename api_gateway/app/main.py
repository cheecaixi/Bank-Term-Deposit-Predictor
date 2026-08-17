from typing import Optional, Literal
from fastapi import FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
import httpx

from app.config import settings

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
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Load Microservice URLs from shared config
INFERENCE_URL = settings.INFERENCE_SERVICE_URL
DATABASE_URL = settings.DATABASE_SERVICE_URL
MONITORING_URL = settings.MONITORING_SERVICE_URL
TIMEOUT_SECONDS = settings.TIMEOUT_SECONDS


# ----------------------------------------------------
# PYDANTIC SCHEMAS FOR DATA VALIDATION
# ----------------------------------------------------
class CustomerPredictModel(BaseModel):
    phone_number: str = Field(..., example="91234567")
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
    phone_number: Optional[str] = Field(None, example="91234567")
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
    async with httpx.AsyncClient() as client:
        payload = customer_data.model_dump()
        
        # Exclude non-inference fields (phone_number and batch_id)
        inference_payload = {
            field: value
            for field, value in payload.items()
            if field not in ("phone_number", "batch_id")
        }

        # Step A: Request prediction from Member A (AI Inference)
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

        # Step B: Persist customer, campaign, and prediction data to Member D.
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

                # Update existing customer's batch_id if provided
                if payload.get("batch_id"):
                    await client.put(
                        f"{DATABASE_URL}/customers/{customer_id}",
                        json={"batch_id": payload["batch_id"]},
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
# 3. BATCH UPLOADS ENDPOINTS (FORWARD TO MEMBER D)
# ----------------------------------------------------
@app.post("/api/batch-uploads")
async def create_batch_upload(batch: BatchUploadModel):
    """
    Register a new batch upload record in Member D.
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


@app.get("/api/batch-uploads/{batch_id}/customers")
async def get_customers_by_batch(batch_id: int):
    """
    Fetch all customer records associated with a specific batch ID from Member D.
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


@app.get("/api/batch-uploads/{batch_id}/results")
async def get_results_by_batch(batch_id: int):
    """
    Fetch joined customer and prediction results for a specific batch ID from Member D.
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
# 4. GET HISTORICAL RECORDS (FORWARD TO MEMBER D)
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
# 5. SEARCH CUSTOMER BY PHONE NUMBER
# ----------------------------------------------------
@app.get("/api/customers/phone/{phone_number}")
async def get_customer_by_phone(phone_number: str):
    """
    Search for an existing customer by phone number.
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
# 6. UPDATE CUSTOMER RECORD (PUT -> MEMBER D)
# ----------------------------------------------------
@app.put("/api/customers/{customer_id}")
async def update_customer(
    customer_id: int,
    updated_data: CustomerUpdateModel
):
    """
    Receives updated customer records from Member C (Dashboard)
    and forwards the PUT request to Member D (Database Service).
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
# 7. DELETE CUSTOMER RECORD (DELETE -> MEMBER D)
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
# 8. GET SYSTEM LOGS (FORWARD TO MEMBER D MONITORING)
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