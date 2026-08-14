from fastapi import (
    APIRouter,
    Depends,
    HTTPException
)

from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError

from app.database import get_db

from app.models import (
    Customer,
    CampaignHistory,
    Prediction,
    BatchUpload,
    HistoricalData
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
    HistoricalDataCreate,
    HistoricalDataResponse
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
        raise HTTPException(
            status_code=500,
            detail="Unable to create customer due to a database error"
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

    # Make sure campaign data exists
    campaign = (
        db.query(CampaignHistory)
        .filter(
            CampaignHistory.customer_id
            == data.customer_id
        )
        .first()
    )

    if campaign is None:
        raise HTTPException(
            status_code=400,
            detail="Customer does not have campaign data yet"
        )

    prediction = Prediction(
        **data.model_dump()
    )

    db.add(prediction)

    # Once prediction is successfully stored
    customer.prediction_status = "COMPLETED"

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

    batch = BatchUpload(
        **data.model_dump()
    )

    db.add(batch)
    db.commit()
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
            Prediction
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

    for customer, prediction in results:

        response.append({
            "customer_id": customer.customer_id,
            "phone_number": customer.phone_number,

            "age": customer.age,
            "job": customer.job,

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


# ============================================================
# HISTORICAL DATA
# ============================================================

@router.post(
    "/historical-data",
    response_model=HistoricalDataResponse,
    tags=["Historical Data"]
)
def create_historical_record(
    data: HistoricalDataCreate,
    db: Session = Depends(get_db)
):

    record = HistoricalData(
        **data.model_dump()
    )

    db.add(record)
    db.commit()
    db.refresh(record)

    return record


@router.get(
    "/historical-data",
    tags=["Historical Data"]
)
def get_historical_data(
    db: Session = Depends(get_db)
):

    return db.query(HistoricalData).all()
