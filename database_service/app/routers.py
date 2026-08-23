from fastapi import (
    APIRouter,
    Depends,
    HTTPException
)

from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError, SQLAlchemyError

from app.database import get_db

from app.models import (
    Customer,
    CampaignHistory,
    Prediction,
    BatchUpload
)

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


router = APIRouter()


# ============================================================
# CUSTOMERS
# ============================================================

@router.post(
    "/customers",
    response_model=CustomerResponse,
    tags=["Customers"]
)
def create_customer(
    data: CustomerCreate,
    db: Session = Depends(get_db)
):
    try:
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

        customer = Customer(**data.model_dump())

        db.add(customer)
        db.commit()
        db.refresh(customer)

        return customer

    except HTTPException:
        raise
    except SQLAlchemyError as exc:
        db.rollback()

        print("DATABASE ERROR:")
        print(repr(exc))

        raise HTTPException(
            status_code=500,
            detail=f"Database error: {str(exc)}"
        ) from exc

@router.get(
    "/customers",
    tags=["Customers"]
)
def get_all_customers(
    db: Session = Depends(get_db)
):

    return db.query(Customer).all()


@router.get(
    "/customers/pending",
    tags=["Customers"]
)
def get_pending_customers(
    db: Session = Depends(get_db)
):

    return (
        db.query(Customer)
        .filter(
            Customer.prediction_status == "PENDING"
        )
        .all()
    )


@router.get(
    "/customers/{customer_id}",
    tags=["Customers"]
)
def get_customer(
    customer_id: int,
    db: Session = Depends(get_db)
):

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

    return customer


@router.put(
    "/customers/{customer_id}",
    tags=["Customers"]
)
def update_customer(
    customer_id: int,
    data: CustomerUpdate,
    db: Session = Depends(get_db)
):

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

    update_data = data.model_dump(
        exclude_unset=True
    )

    for field, value in update_data.items():
        setattr(
            customer,
            field,
            value
        )

    db.commit()
    db.refresh(customer)

    return customer


@router.delete(
    "/customers/{customer_id}",
    tags=["Customers"]
)
def delete_customer(
    customer_id: int,
    db: Session = Depends(get_db)
):

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

    db.delete(customer)
    db.commit()

    return {
        "message": "Customer deleted successfully",
        "customer_id": customer_id
    }


# ============================================================
# CAMPAIGN HISTORY
# ============================================================
@router.post(
    "/campaign-history",
    response_model=CampaignResponse,
    tags=["Campaign"]
)
def create_campaign_history(
    data: CampaignCreate,
    db: Session = Depends(get_db)
):

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

    # Check if customer already has campaign data
    existing_campaign = (
        db.query(CampaignHistory)
        .filter(
            CampaignHistory.customer_id == data.customer_id
        )
        .first()
    )

    if existing_campaign is not None:

        # Override existing campaign information
        existing_campaign.contact = data.contact
        existing_campaign.day = data.day
        existing_campaign.month = data.month
        existing_campaign.campaign = data.campaign
        existing_campaign.pdays = data.pdays
        existing_campaign.previous = data.previous
        existing_campaign.poutcome = data.poutcome

        campaign = existing_campaign

    else:

        campaign = CampaignHistory(
            **data.model_dump()
        )

        db.add(campaign)

    db.commit()
    db.refresh(campaign)

    return campaign

@router.get(
    "/campaign-history/{customer_id}",
    tags=["Campaign"]
)
def get_customer_campaign_history(
    customer_id: int,
    db: Session = Depends(get_db)
):

    return (
        db.query(CampaignHistory)
        .filter(
            CampaignHistory.customer_id
            == customer_id
        )
        .all()
    )


# ============================================================
# PREDICTIONS
# ============================================================

@router.post(
    "/predictions",
    response_model=PredictionResponse,
    tags=["Predictions"]
)
def save_prediction(
    data: PredictionCreate,
    db: Session = Depends(get_db)
):

    # --------------------------------------------------------
    # 1. Check that customer exists
    # --------------------------------------------------------
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

    # --------------------------------------------------------
    # 2. Make sure campaign data exists
    # --------------------------------------------------------
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

    # --------------------------------------------------------
    # 3. Check whether this customer already has a prediction
    # --------------------------------------------------------
    existing_prediction = (
        db.query(Prediction)
        .filter(
            Prediction.customer_id == data.customer_id
        )
        .first()
    )

    # --------------------------------------------------------
    # 4. UPDATE existing prediction
    # --------------------------------------------------------
    if existing_prediction is not None:

        existing_prediction.prediction = data.prediction
        existing_prediction.probability = data.probability

        prediction = existing_prediction

    # --------------------------------------------------------
    # 5. CREATE prediction if customer has none
    # --------------------------------------------------------
    else:

        prediction = Prediction(
            **data.model_dump()
        )

        db.add(prediction)

    # --------------------------------------------------------
    # 6. Mark customer prediction as completed
    # --------------------------------------------------------
    customer.prediction_status = "COMPLETED"

    # --------------------------------------------------------
    # 7. Update batch status
    # --------------------------------------------------------
    if customer.batch_id is not None:

        batch = (
            db.query(BatchUpload)
            .filter(
                BatchUpload.batch_id == customer.batch_id
            )
            .first()
        )

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

        if batch is not None:
            batch.status = (
                "completed"
                if completed_count >= batch.total_records
                else "processing"
            )

    # --------------------------------------------------------
    # 8. Save
    # --------------------------------------------------------
    db.commit()
    db.refresh(prediction)

    return prediction


@router.get(
    "/predictions",
    response_model=list[PredictionResponse],
    tags=["Predictions"]
)
def get_all_predictions(
    db: Session = Depends(get_db)
):

    return db.query(Prediction).all()


@router.get(
    "/predictions/customer/{customer_id}",
    tags=["Predictions"]
)
def get_customer_predictions(
    customer_id: int,
    db: Session = Depends(get_db)
):

    return (
        db.query(Prediction)
        .filter(
            Prediction.customer_id
            == customer_id
        )
        .all()
    )


# ============================================================
# BATCH UPLOADS
# ============================================================

@router.post(
    "/batch-uploads",
    response_model=BatchUploadResponse,
    tags=["Batch Upload"]
)
def create_batch(
    data: BatchUploadCreate,
    db: Session = Depends(get_db)
):

    existing_batch = (
        db.query(BatchUpload)
        .filter(BatchUpload.file_hash == data.file_hash)
        .first()
    )
    if existing_batch is not None:
        raise HTTPException(
            status_code=409,
            detail={
                "message": "CSV file already exists",
                "batch_id": existing_batch.batch_id
            }
        )

    batch = BatchUpload(
        **data.model_dump()
    )

    try:
        db.add(batch)
        db.commit()
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
    db.refresh(batch)

    return batch


@router.get(
    "/batch-uploads",
    tags=["Batch Upload"]
)
def get_batches(
    db: Session = Depends(get_db)
):

    return db.query(BatchUpload).all()


@router.get(
    "/batch-uploads/check/{file_hash}",
    response_model=BatchUploadCheckResponse,
    tags=["Batch Upload"]
)
def check_batch_upload(
    file_hash: str,
    db: Session = Depends(get_db)
):
    if len(file_hash) != 64 or any(
        character not in "0123456789abcdef" for character in file_hash
    ):
        raise HTTPException(status_code=422, detail="Invalid SHA-256 file hash")

    batch = (
        db.query(BatchUpload)
        .filter(BatchUpload.file_hash == file_hash)
        .first()
    )

    if batch is None:
        return {"exists": False}

    return {
        "exists": True,
        "batch_id": batch.batch_id,
        "status": batch.status
    }


@router.get(
    "/batch-uploads/{batch_id}",
    tags=["Batch Upload"]
)
def get_batch(
    batch_id: int,
    db: Session = Depends(get_db)
):

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
# GET CUSTOMERS FROM SPECIFIC BATCH
# ============================================================

@router.get(
    "/batch-uploads/{batch_id}/customers",
    tags=["Batch Upload"]
)
def get_batch_customers(
    batch_id: int,
    db: Session = Depends(get_db)
):

    customers = (
        db.query(Customer)
        .filter(
            Customer.batch_id == batch_id
        )
        .all()
    )

    return customers


# ============================================================
# GET RESULTS FROM SPECIFIC BATCH
# ============================================================

@router.get(
    "/batch-uploads/{batch_id}/results",
    tags=["Batch Upload"]
)
def get_batch_results(
    batch_id: int,
    db: Session = Depends(get_db)
):

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

    return {
        "batch_id": batch.batch_id,
        "file_name": batch.file_name,
        "total_records": batch.total_records,
        "results": response
    }
