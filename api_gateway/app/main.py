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
#
# NOTE: allow_credentials=False here because allow_origins="*" and
# allow_credentials=True together are invalid per the CORS spec --
# browsers will silently block credentialed requests in that combination.
# If Member C's dashboard ever needs to send cookies or an Authorization
# header, allow_origins must be changed to the dashboard's exact origin
# (e.g. ["http://localhost:3000"]) and allow_credentials set to True.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Load Microservice URLs from shared config (single source of truth,
# instead of duplicating os.getenv calls here and in config.py)
INFERENCE_URL = settings.INFERENCE_SERVICE_URL
DATABASE_URL = settings.DATABASE_SERVICE_URL
MONITORING_URL = settings.MONITORING_SERVICE_URL
TIMEOUT_SECONDS = settings.TIMEOUT_SECONDS


# ----------------------------------------------------
# PYDANTIC SCHEMAS FOR DATA VALIDATION
#
# Categorical fields use the same Literal values as Member A's
# CustomerData schema (inference/schemas.py), confirmed against
# the actual training dataset. This means bad category values are
# rejected here with a 422, instead of round-tripping to the
# inference service first and forwarding its error back.
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
        inference_payload = {
            field: value
            for field, value in payload.items()
            if field != "phone_number"
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
                    "default", "balance", "housing", "loan"
                )
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
# 4. SEARCH CUSTOMER BY PHONE NUMBER
# ----------------------------------------------------
@app.get("/api/customers/phone/{phone_number}")
async def get_customer_by_phone(phone_number: str):
    """
    Search for an existing customer by phone number.

    Member C (Dashboard) calls this endpoint.
    The API Gateway forwards the request to Member D
    and returns the matching customer.
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
                    if str(item.get("phone_number", "")).strip()
                    == phone_number.strip()
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
                detail=(
                    "Member D (Database Service) error: "
                    f"{exc.response.text}"
                )
            )

        except httpx.RequestError as exc:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=(
                    "Member D (Database Service) unreachable: "
                    f"{exc}"
                )
            )


# ----------------------------------------------------
# 5. UPDATE CUSTOMER RECORD (PUT -> MEMBER D)
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
                detail=(
                    f"Database Service error: "
                    f"{exc.response.text}"
                )
            )

        except httpx.RequestError as exc:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=(
                    "Member D (Database Service) unreachable: "
                    f"{exc}"
                )
            )


# ----------------------------------------------------
# 6. DELETE CUSTOMER RECORD (DELETE -> MEMBER D)
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
                detail=(
                    f"Database Service error: "
                    f"{exc.response.text}"
                )
            )

        except httpx.RequestError as exc:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=(
                    "Member D (Database Service) unreachable: "
                    f"{exc}"
                )
            )

# ----------------------------------------------------
# 7. GET SYSTEM LOGS (FORWARD TO MEMBER D MONITORING)
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