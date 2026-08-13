from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict


# ============================================================
# CUSTOMER
# ============================================================

class CustomerCreate(BaseModel):
    phone_number: str

    age: int
    job: str
    marital: str
    education: str

    default: str
    balance: float
    housing: str
    loan: str

    batch_id: Optional[int] = None


class CustomerUpdate(BaseModel):
    phone_number: Optional[str] = None

    age: Optional[int] = None
    job: Optional[str] = None
    marital: Optional[str] = None
    education: Optional[str] = None

    default: Optional[str] = None
    balance: Optional[float] = None
    housing: Optional[str] = None
    loan: Optional[str] = None


class CustomerResponse(CustomerCreate):
    customer_id: int
    prediction_status: str
    created_at: datetime

    model_config = ConfigDict(
        from_attributes=True
    )


# ============================================================
# CAMPAIGN HISTORY
# ============================================================

class CampaignCreate(BaseModel):
    customer_id: int

    contact: str
    day: int
    month: str

    campaign: int
    pdays: int
    previous: int

    poutcome: str


class CampaignResponse(CampaignCreate):
    campaign_id: int
    created_at: datetime

    model_config = ConfigDict(
        from_attributes=True
    )


# ============================================================
# PREDICTION
# ============================================================

class PredictionCreate(BaseModel):
    customer_id: int

    prediction: str
    probability: float

    model_version: Optional[str] = None


class PredictionResponse(PredictionCreate):
    prediction_id: int
    predicted_at: datetime

    model_config = ConfigDict(
        from_attributes=True
    )


# ============================================================
# BATCH UPLOAD
# ============================================================

class BatchUploadCreate(BaseModel):
    file_name: str
    total_records: int


class BatchUploadResponse(BatchUploadCreate):
    batch_id: int
    uploaded_at: datetime

    model_config = ConfigDict(
        from_attributes=True
    )


# ============================================================
# HISTORICAL DATA
# ============================================================

class HistoricalDataCreate(BaseModel):
    age: int
    job: str
    marital: str
    education: str

    default: str
    balance: float

    housing: str
    loan: str

    contact: str
    day: int
    month: str

    campaign: int
    pdays: int
    previous: int

    poutcome: str

    actual_subscription: str

    predicted_subscription: Optional[str] = None

    prediction_probability: Optional[float] = None


class HistoricalDataResponse(HistoricalDataCreate):
    historical_id: int

    model_config = ConfigDict(
        from_attributes=True
    )
