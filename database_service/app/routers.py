# Defines all API endpoints for the Database Service.
# Handles CRUD operations for customers, campaign history, predictions, and batch uploads,
# including data validation, duplicate detection, database error handling,
# prediction progress tracking, and retrieval of batch results.

from fastapi import (
    APIRouter,
    Depends,
    HTTPException
)

from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError, SQLAlchemyError

# Import the database session dependency.
# Each API request uses this to communicate with the PostgreSQL database.
from app.database import get_db

# Import SQLAlchemy database models used to query and modify the tables.
from app.models import (
    Customer,
    CampaignHistory,
    Prediction,
    BatchUpload
)

# Import Pydantic schemas used to validate incoming request data
# and control the structure of API responses.
from app.schemas import (
    CustomerCreate,
    CustomerUpdate,
    CustomerResponse,
    CampaignCreate,
    CampaignResponse,
    PredictionCreate,
    PredictionResponse,
    BatchUploadCreate,
    BatchUploadResponse,
    BatchUploadCheckResponse
)

# Create a shared API router.
# All endpoints defined below are registered to this router
# and later connected to the main FastAPI application.
router = APIRouter()


# ============================================================
# CUSTOMERS - Handles creating, retrieving, updating, and deleting customers.
# ============================================================

# POST /customers
# Creates and stores a new customer in the database.
@router.post(
    "/customers",
    response_model=CustomerResponse,
    tags=["Customers"]
)
def create_customer(
    data: CustomerCreate,
    db: Session = Depends(get_db)
):
    """Create a unique customer after optionally validating its batch."""

    try:
        # Check whether another customer already uses the same phone number.
        # Phone numbers are unique, so duplicate customers are rejected.
        existing_customer = (
            db.query(Customer)
            .filter(Customer.phone_number == data.phone_number)
            .first()
        )

        if existing_customer:
            raise HTTPException(
                status_code=409,
                detail="Customer with this phone number already exists"
            )

        # If the customer came from a CSV batch,
        # verify that the referenced batch actually exists.
        if data.batch_id is not None:
            batch = (
                db.query(BatchUpload)
                .filter(BatchUpload.batch_id == data.batch_id)
                .first()
            )

            if batch is None:
                raise HTTPException(
                    status_code=404,
                    detail="Batch not found"
                )
        # Convert the validated Pydantic input into a SQLAlchemy Customer object.
        customer = Customer(**data.model_dump())

        db.add(customer)
        db.commit()
        db.refresh(customer)

        return customer

     # Re-raise expected API errors such as 404 or 409.
    except HTTPException:
        raise
    # Handle unexpected database errors safely.
    # Rollback prevents a failed transaction from affecting later operations.
    except SQLAlchemyError as exc:
        db.rollback()

        print("DATABASE ERROR:")
        print(repr(exc))

        raise HTTPException(
            status_code=500,
            detail=f"Database error: {str(exc)}"
        ) from exc

# GET /customers
# Retrieves all customers currently stored in the database.
@router.get(
    "/customers",
    tags=["Customers"]
)
def get_all_customers(
    db: Session = Depends(get_db)
):
    """Return every stored customer."""

    return db.query(Customer).all()

# GET /customers/pending
# Retrieves only customers that are still waiting for AI predictions.
@router.get(
    "/customers/pending",
    tags=["Customers"]
)
def get_pending_customers(
    db: Session = Depends(get_db)
):
    """Return customers that do not yet have a completed prediction."""

    return (
        db.query(Customer)
        .filter(
            Customer.prediction_status == "PENDING"
        )
        .all()
    )

# GET /customers/{customer_id}
# Retrieves one specific customer using their unique customer ID.
@router.get(
    "/customers/{customer_id}",
    tags=["Customers"]
)
def get_customer(
    customer_id: int,
    db: Session = Depends(get_db)
):
    """Return one customer by ID or respond with 404 when absent."""

    customer = (
        db.query(Customer)
        .filter(
            Customer.customer_id == customer_id
        )
        .first()
    )

    # Return 404 if the requested customer does not exist.
    if customer is None:
        raise HTTPException(
            status_code=404,
            detail="Customer not found"
        )

    return customer

# PUT /customers/{customer_id}
# Updates selected fields of an existing customer.
@router.put(
    "/customers/{customer_id}",
    tags=["Customers"]
)
def update_customer(
    customer_id: int,
    data: CustomerUpdate,
    db: Session = Depends(get_db)
):
    """Apply only the customer fields supplied in a partial update request."""
     # Find the customer that needs to be updated.
    customer = (
        db.query(Customer)
        .filter(
            Customer.customer_id == customer_id
        )
        .first()
    )

    if customer is None:
        raise HTTPException(
            status_code=404,
            detail="Customer not found"
        )
    # Only include fields that were actually supplied in the request.
    # This prevents unspecified fields from being overwritten.
    update_data = data.model_dump(
        exclude_unset=True
    )
    # Dynamically update each supplied customer field.
    for field, value in update_data.items():
        setattr(
            customer,
            field,
            value
        )
    # Save changes and refresh the updated customer.
    db.commit()
    db.refresh(customer)

    return customer


# DELETE /customers/{customer_id}
# Deletes a customer from the database.
@router.delete(
    "/customers/{customer_id}",
    tags=["Customers"]
)
def delete_customer(
    customer_id: int,
    db: Session = Depends(get_db)
):
    """Delete a customer and cascade deletion to related child records."""

    customer = (
        db.query(Customer)
        .filter(
            Customer.customer_id == customer_id
        )
        .first()
    )

    if customer is None:
        raise HTTPException(
            status_code=404,
            detail="Customer not found"
        )
    # Delete the customer.
    # Related campaign and prediction records are also removed
    # because cascade deletion is configured in the Customer model.
    db.delete(customer)
    db.commit()

    return {
        "message": "Customer deleted successfully",
        "customer_id": customer_id
    }


# ============================================================
# CAMPAIGN HISTORY - Stores and retrieves marketing campaign data for customers.
# ============================================================
# POST /campaign-history
# Creates campaign information for an existing customer.
@router.post(
    "/campaign-history",
    response_model=CampaignResponse,
    tags=["Campaign"]
)
def create_campaign_history(
    data: CampaignCreate,
    db: Session = Depends(get_db)
):
    """Attach a set of marketing campaign inputs to an existing customer."""
    # Verify that the customer exists before attaching campaign data.
    customer = (
        db.query(Customer)
        .filter(
            Customer.customer_id == data.customer_id
        )
        .first()
    )

    if customer is None:
        raise HTTPException(
            status_code=404,
            detail="Customer not found"
        )
    # Update the customer's existing campaign instead of creating a duplicate.
    existing_campaign = (
        db.query(CampaignHistory)
        .filter(
            CampaignHistory.customer_id == data.customer_id
        )
        .first()
    )

    if existing_campaign is not None:

        # Replace the old campaign values with the latest submitted values.
        existing_campaign.contact = data.contact
        existing_campaign.day = data.day
        existing_campaign.month = data.month
        existing_campaign.campaign = data.campaign
        existing_campaign.pdays = data.pdays
        existing_campaign.previous = data.previous
        existing_campaign.poutcome = data.poutcome

        campaign = existing_campaign

    else:
        # Create the first campaign record for this customer.
        campaign = CampaignHistory(
            **data.model_dump()
        )

        db.add(campaign)

    db.commit()
    db.refresh(campaign)

    return campaign

# GET /campaign-history/{customer_id}
# Retrieves all campaign records belonging to a specific customer.
@router.get(
    "/campaign-history/{customer_id}",
    tags=["Campaign"]
)
def get_customer_campaign_history(
    customer_id: int,
    db: Session = Depends(get_db)
):
    """Return all campaign records associated with a customer."""

    return (
        db.query(CampaignHistory)
        .filter(
            CampaignHistory.customer_id
            == customer_id
        )
        .all()
    )


# ============================================================
# PREDICTIONS - Stores AI prediction results and updates prediction progress.
# ============================================================

# POST /predictions
# Saves a prediction generated by the AI service.
@router.post(
    "/predictions",
    response_model=PredictionResponse,
    tags=["Predictions"]
)
def save_prediction(
    data: PredictionCreate,
    db: Session = Depends(get_db)
):
    """Persist a prediction and update its customer and batch progress."""
    # Verify that the customer receiving the prediction exists.
    customer = (
        db.query(Customer)
        .filter(
            Customer.customer_id == data.customer_id
        )
        .first()
    )

    if customer is None:
        raise HTTPException(
            status_code=404,
            detail="Customer not found"
        )

    # Make sure campaign information exists before saving a prediction.
    # Campaign data contains features required for the prediction process.
    campaign = (
        db.query(CampaignHistory)
        .filter(
            CampaignHistory.customer_id == data.customer_id
        )
        .first()
    )

    if campaign is None:
        raise HTTPException(
            status_code=400,
            detail="Customer does not have campaign data yet"
        )
    # Check whether this customer already has a stored prediction.
    existing_prediction = (
        db.query(Prediction)
        .filter(
            Prediction.customer_id == data.customer_id
        )
        .first()
    )

    if existing_prediction is not None:
        # Replace the old result when the customer is predicted again.
        existing_prediction.prediction = data.prediction
        existing_prediction.probability = data.probability

        prediction = existing_prediction

    else:
        # Create the customer's first prediction record.
        prediction = Prediction(
            **data.model_dump()
        )

        db.add(prediction)

    # Mark the customer as completed because a prediction is now stored.
    customer.prediction_status = "COMPLETED"

    # If the customer came from a CSV batch, update that batch's progress.
    if customer.batch_id is not None:
        batch = (
            db.query(BatchUpload)
            .filter(
                BatchUpload.batch_id == customer.batch_id
            )
            .first()
        )

        # Count how many predictions have been completed
        # for customers belonging to this batch.
        completed_count = (
            db.query(Prediction)
            .join(
                Customer,
                Customer.customer_id == Prediction.customer_id
            )
            .filter(
                Customer.batch_id == customer.batch_id
            )
            .count()
        )

        # If all expected records have predictions, mark the batch completed.
        # Otherwise, the batch remains in processing.
        if batch is not None:
            batch.status = (
                "completed"
                if completed_count >= batch.total_records
                else "processing"
            )
    # Save the prediction and all related status changes together.
    db.commit()
    db.refresh(prediction)

    return prediction

# GET /predictions
# Retrieves every prediction stored by the service.
@router.get(
    "/predictions",
    response_model=list[PredictionResponse],
    tags=["Predictions"]
)
def get_all_predictions(
    db: Session = Depends(get_db)
):
    """Return every prediction stored by the service."""

    return db.query(Prediction).all()

# GET /predictions/customer/{customer_id}
# Retrieves the prediction history of one customer.
@router.get(
    "/predictions/customer/{customer_id}",
    tags=["Predictions"]
)
def get_customer_predictions(
    customer_id: int,
    db: Session = Depends(get_db)
):
    """Return the prediction history for one customer."""

    return (
        db.query(Prediction)
        .filter(
            Prediction.customer_id
            == customer_id
        )
        .all()
    )


# ============================================================
# BATCH UPLOADS - anages CSV batch registration, duplicate checking, and progress.
# ============================================================

# POST /batch-uploads
# Registers a newly uploaded CSV file as a batch.
@router.post(
    "/batch-uploads",
    response_model=BatchUploadResponse,
    tags=["Batch Upload"]
)
def create_batch(
    data: BatchUploadCreate,
    db: Session = Depends(get_db)
):
    """Register a CSV batch while rejecting duplicate file contents."""
     # Check the SHA-256 file hash before creating the batch.
    # If the hash already exists, the same CSV content was uploaded before.
    existing_batch = (
        db.query(BatchUpload)
        .filter(BatchUpload.file_hash == data.file_hash)
        .first()
    )
    # Return HTTP 409 Conflict when a duplicate CSV is detected.
    if existing_batch is not None:
        raise HTTPException(
            status_code=409,
            detail={
                "message": "CSV file already exists",
                "batch_id": existing_batch.batch_id
            }
        )
    # Create a new BatchUpload database object from validated input.
    batch = BatchUpload(
        **data.model_dump()
    )

    try:
        # Attempt to save the new batch.
        db.add(batch)
        db.commit()

    # The database also has a UNIQUE constraint on file_hash.
    # This catches duplicate uploads even if two requests happen at the same time.
    except IntegrityError:
        db.rollback()
        existing_batch = (
            db.query(BatchUpload)
            .filter(BatchUpload.file_hash == data.file_hash)
            .first()
        )
        raise HTTPException(
            status_code=409,
            detail={
                "message": "CSV file already exists",
                "batch_id": (
                    existing_batch.batch_id
                    if existing_batch is not None
                    else None
                )
            }
        )
    # Reload database-generated values such as batch_id.
    db.refresh(batch)

    return batch

# GET /batch-uploads
# Retrieves information and processing status for every uploaded batch
@router.get(
    "/batch-uploads",
    tags=["Batch Upload"]
)
def get_batches(
    db: Session = Depends(get_db)
):
    """Return metadata and processing status for all batches."""

    return db.query(BatchUpload).all()

# GET /batch-uploads/check/{file_hash}
# Checks whether a CSV with the supplied SHA-256 hash was already uploaded.
@router.get(
    "/batch-uploads/check/{file_hash}",
    response_model=BatchUploadCheckResponse,
    tags=["Batch Upload"]
)
def check_batch_upload(
    file_hash: str,
    db: Session = Depends(get_db)
):
    """Validate a SHA-256 hash and report whether its batch already exists."""
    # A SHA-256 hash must contain exactly 64 hexadecimal characters.
    # Reject incorrectly formatted hashes before querying the database.
    if len(file_hash) != 64 or any(
        character not in "0123456789abcdef" for character in file_hash
    ):
        raise HTTPException(status_code=422, detail="Invalid SHA-256 file hash")
    # Search for an existing batch with the same file hash.
    batch = (
        db.query(BatchUpload)
        .filter(BatchUpload.file_hash == file_hash)
        .first()
    )
    # If no matching hash exists, the file has not been uploaded before.
    if batch is None:
        return {"exists": False}

     # If it exists, return its batch ID and current processing status.
    return {
        "exists": True,
        "batch_id": batch.batch_id,
        "status": batch.status
    }

# GET /batch-uploads/{batch_id}
# Retrieves information about one specific batch.
@router.get(
    "/batch-uploads/{batch_id}",
    tags=["Batch Upload"]
)
def get_batch(
    batch_id: int,
    db: Session = Depends(get_db)
):
    """Return one batch by ID or respond with 404 when absent."""

    batch = (
        db.query(BatchUpload)
        .filter(
            BatchUpload.batch_id == batch_id
        )
        .first()
    )

    if batch is None:
        raise HTTPException(
            status_code=404,
            detail="Batch not found"
        )

    return batch


# ============================================================
# GET CUSTOMERS FROM SPECIFIC BATCH - Retrieves customers that were imported from one CSV batch.
# ============================================================
# GET /batch-uploads/{batch_id}/customers
# Returns all customers associated with the requested batch ID.
@router.get(
    "/batch-uploads/{batch_id}/customers",
    tags=["Batch Upload"]
)
def get_batch_customers(
    batch_id: int,
    db: Session = Depends(get_db)
):
    """Return all customers imported as part of a particular batch."""

    batch = (
        db.query(BatchUpload)
        .filter(
            BatchUpload.batch_id == batch_id
        )
        .first()
    )

    if batch is None:
        raise HTTPException(
            status_code=404,
            detail="Batch not found"
        )

    results = (
        db.query(
            Customer,
            CampaignHistory
        )
        .join(
            CampaignHistory,
            Customer.customer_id
            == CampaignHistory.customer_id
        )
        .filter(
            Customer.batch_id == batch_id
        )
        .all()
    )

    response = []

    for customer, campaign in results:

        response.append({

            # Identification
            "customer_id": customer.customer_id,
            "phone_number": customer.phone_number,
            "batch_id": customer.batch_id,

            # 15 prediction features
            "age": customer.age,
            "job": customer.job,
            "marital": customer.marital,
            "education": customer.education,
            "default": customer.default,
            "balance": customer.balance,
            "housing": customer.housing,
            "loan": customer.loan,

            "contact": campaign.contact,
            "day": campaign.day,
            "month": campaign.month,
            "campaign": campaign.campaign,
            "pdays": campaign.pdays,
            "previous": campaign.previous,
            "poutcome": campaign.poutcome,

            # Status
            "prediction_status": customer.prediction_status
        })

    return response


# ============================================================
# GET RESULTS FROM SPECIFIC BATCH - Combines customer information with their prediction results.
# ============================================================

# GET /batch-uploads/{batch_id}/results
# Retrieves the final prediction results for a specific CSV batch.
@router.get(
    "/batch-uploads/{batch_id}/results",
    tags=["Batch Upload"]
)
def get_batch_results(
    batch_id: int,
    db: Session = Depends(get_db)
):
    """Join customers with predictions to build a batch result summary."""
    # Verify that the requested batch exists.
    batch = (
        db.query(BatchUpload)
        .filter(
            BatchUpload.batch_id == batch_id
        )
        .first()
    )

    if batch is None:
        raise HTTPException(
            status_code=404,
            detail="Batch not found"
        )
    # Join Customer and Prediction using customer_id.
    # Only records belonging to the requested batch are returned.
    results = (
        db.query(
            Customer,
            CampaignHistory,
            Prediction
        )
        .join(
            CampaignHistory,
            Customer.customer_id
            == CampaignHistory.customer_id
        )
        .join(
            Prediction,
            Customer.customer_id
            == Prediction.customer_id
        )
        .filter(
            Customer.batch_id == batch_id
        )
        .all()
    )
    # Build a clean response containing the important customer
    # information together with their prediction result.
    response = []

    for customer, campaign, prediction in results:

        response.append({
            # Identification
            "customer_id": customer.customer_id,
            "phone_number": customer.phone_number,

            # 15 prediction features
            "age": customer.age,
            "job": customer.job,
            "marital": customer.marital,
            "education": customer.education,
            "default": customer.default,
            "balance": customer.balance,
            "housing": customer.housing,
            "loan": customer.loan,

            "contact": campaign.contact,
            "day": campaign.day,
            "month": campaign.month,
            "campaign": campaign.campaign,
            "pdays": campaign.pdays,
            "previous": campaign.previous,
            "poutcome": campaign.poutcome,

            # Prediction result
            "prediction": prediction.prediction,
            "probability": prediction.probability,
            "predicted_at": prediction.predicted_at
        })
    # Return batch information together with all prediction results.
    return {
        "batch_id": batch.batch_id,
        "file_name": batch.file_name,
        "total_records": batch.total_records,
        "results": response
    }
