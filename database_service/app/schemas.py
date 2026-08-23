# Defines the Pydantic schemas used by the Database Service.
# These schemas validate incoming API request data and control the structure
# of API responses for customers, campaigns, predictions, and batch uploads.
from datetime import datetime
from typing import Optional

# BaseModel is the base class for Pydantic validation schemas.
# ConfigDict controls schema behaviour, while Field adds validation rules.
from pydantic import BaseModel, ConfigDict, Field


# ============================================================
# CUSTOMER - Defines request and response structures for customer data.
# ============================================================

class CustomerCreate(BaseModel):
    """Validate the customer details required when creating a record."""

    # Customer information required when creating a new customer.
    phone_number: str

    age: int
    job: str
    marital: str
    education: str

    default: str
    balance: float
    housing: str
    loan: str

    # batch_id is optional because customers can either come from
    # a CSV batch or be entered manually.
    # gt=0 ensures that a supplied batch ID must be greater than zero.
    batch_id: Optional[int] = Field(default=None, gt=0)

    # Provides example request data in the automatic FastAPI documentation.
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "phone_number": "91234567",
                "age": 35,
                "job": "management",
                "marital": "married",
                "education": "tertiary",
                "default": "no",
                "balance": 1500,
                "housing": "yes",
                "loan": "no"
            }
        }
    )


class CustomerUpdate(BaseModel):
    """Accept a partial set of editable customer fields."""

    # All fields are optional because an update request may change
    # only one or a few customer attributes instead of the whole record.
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
    """Return customer input fields together with database-generated values."""
    # Inherits the fields from CustomerCreate and adds values
    # that are generated or maintained by the database.
    customer_id: int
    prediction_status: str
    created_at: datetime

    # Allows Pydantic to create the response directly from
    # SQLAlchemy Customer objects returned by the database.
    model_config = ConfigDict(
        from_attributes=True
    )


# ============================================================
# CAMPAIGN HISTORY - Defines request and response structures for campaign information.
# ============================================================

class CampaignCreate(BaseModel):
    """Validate campaign attributes associated with an existing customer."""

     # Links the campaign information to an existing customer.
    customer_id: int

    # Marketing campaign features used as inputs for prediction.
    contact: str
    day: int
    month: str

    campaign: int
    pdays: int
    previous: int

    poutcome: str


class CampaignResponse(CampaignCreate):
    """Return campaign data with its identifier and creation time."""

    # Inherits the campaign input fields and adds
    # database-generated information to the API response.
    campaign_id: int
    created_at: datetime

    # Allows SQLAlchemy CampaignHistory objects
    # to be converted into Pydantic API responses.
    model_config = ConfigDict(
        from_attributes=True
    )


# ============================================================
# PREDICTION -  Defines request and response structures for AI predictions.
# ============================================================

class PredictionCreate(BaseModel):
    """Validate an AI prediction before it is persisted."""

    # Identifies which customer this prediction belongs to.
    customer_id: int

    # Prediction result and confidence/probability
    # returned by the AI model.
    prediction: str
    probability: float

    # Model version is optional so the service can record
    # which AI model generated the prediction when available.
    model_version: Optional[str] = None


class PredictionResponse(PredictionCreate):
    """Return a stored prediction with its identifier and timestamp."""

    # Inherits prediction input fields and adds values
    # generated when the prediction is stored.
    prediction_id: int
    predicted_at: datetime

    # Allows Pydantic to convert SQLAlchemy Prediction objects
    # directly into API response objects.
    model_config = ConfigDict(
        from_attributes=True
    )


# ============================================================
# BATCH UPLOAD - Defines validation and responses for CSV batch uploads.
# ============================================================

class BatchUploadCreate(BaseModel):
    """Validate uploaded-file metadata, including its SHA-256 fingerprint."""
    # Store basic information about the uploaded CSV.
    file_name: str
    total_records: int

    # Validate the SHA-256 hash used for duplicate-file detection.
    # SHA-256 produces exactly 64 hexadecimal characters.
    file_hash: str = Field(
        min_length=64,
        max_length=64,
        pattern=r"^[0-9a-f]{64}$"
    )


class BatchUploadResponse(BatchUploadCreate):
    """Return batch metadata together with progress and audit timestamps."""
    # Inherits the uploaded file information and adds
    # database-generated batch information.
    batch_id: int
    status: str
    created_at: datetime
    uploaded_at: datetime

    # Allows SQLAlchemy BatchUpload objects to be
    # converted directly into API responses.
    model_config = ConfigDict(
        from_attributes=True
    )


class BatchUploadCheckResponse(BaseModel):
    """Describe whether a file hash already belongs to a stored batch."""
    # Always tells the caller whether the uploaded file already exists.
    exists: bool

    # These values are optional because they are only available
    # when a matching batch already exists.
    batch_id: Optional[int] = None
    status: Optional[str] = None
