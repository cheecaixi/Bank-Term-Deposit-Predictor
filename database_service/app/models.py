from datetime import datetime

from sqlalchemy import (
    Column,
    Integer,
    String,
    Float,
    DateTime,
    ForeignKey
)

from sqlalchemy.orm import relationship

from app.database import Base


# ============================================================
# 1. HISTORICAL DATA
# ============================================================

class HistoricalData(Base):
    __tablename__ = "historical_data"

    historical_id = Column(
        Integer,
        primary_key=True,
        index=True
    )

    # Customer information
    age = Column(Integer, nullable=False)
    job = Column(String(50), nullable=False)
    marital = Column(String(30), nullable=False)
    education = Column(String(50), nullable=False)

    default = Column(String(10), nullable=False)

    balance = Column(Float, nullable=False)

    housing = Column(String(10), nullable=False)
    loan = Column(String(10), nullable=False)

    # Campaign information
    contact = Column(String(30), nullable=False)
    day = Column(Integer, nullable=False)
    month = Column(String(20), nullable=False)

    campaign = Column(Integer, nullable=False)
    pdays = Column(Integer, nullable=False)
    previous = Column(Integer, nullable=False)

    poutcome = Column(String(30), nullable=False)

    # Original actual result from dataset
    actual_subscription = Column(
        String(10),
        nullable=False
    )

    # Student A's model prediction
    predicted_subscription = Column(
        String(10),
        nullable=True
    )

    prediction_probability = Column(
        Float,
        nullable=True
    )


# ============================================================
# 2. BATCH UPLOADS
# ============================================================

class BatchUpload(Base):
    __tablename__ = "batch_uploads"

    batch_id = Column(
        Integer,
        primary_key=True,
        index=True
    )

    file_name = Column(
        String(255),
        nullable=False
    )

    total_records = Column(
        Integer,
        nullable=False
    )

    uploaded_at = Column(
        DateTime,
        default=datetime.utcnow,
        nullable=False
    )

    customers = relationship(
        "Customer",
        back_populates="batch"
    )


# ============================================================
# 3. CUSTOMERS
# ============================================================

class Customer(Base):
    __tablename__ = "customers"

    customer_id = Column(
        Integer,
        primary_key=True,
        index=True
    )

    phone_number = Column(
        String(30),
        unique=True,
        nullable=False
    )

    # NULL = manual input
    # Number = came from CSV batch
    batch_id = Column(
        Integer,
        ForeignKey("batch_uploads.batch_id"),
        nullable=True
    )

    age = Column(Integer, nullable=False)

    job = Column(
        String(50),
        nullable=False
    )

    marital = Column(
        String(30),
        nullable=False
    )

    education = Column(
        String(50),
        nullable=False
    )

    default = Column(
        String(10),
        nullable=False
    )

    balance = Column(
        Float,
        nullable=False
    )

    housing = Column(
        String(10),
        nullable=False
    )

    loan = Column(
        String(10),
        nullable=False
    )

    # PENDING = no completed prediction yet
    # COMPLETED = prediction generated
    prediction_status = Column(
        String(20),
        default="PENDING",
        nullable=False
    )

    created_at = Column(
        DateTime,
        default=datetime.utcnow,
        nullable=False
    )

    updated_at = Column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=False
    )

    batch = relationship(
        "BatchUpload",
        back_populates="customers"
    )

    campaign_history = relationship(
        "CampaignHistory",
        back_populates="customer",
        cascade="all, delete-orphan"
    )

    predictions = relationship(
        "Prediction",
        back_populates="customer",
        cascade="all, delete-orphan"
    )


# ============================================================
# 4. CAMPAIGN HISTORY
# ============================================================

class CampaignHistory(Base):
    __tablename__ = "campaign_history"

    campaign_id = Column(
        Integer,
        primary_key=True,
        index=True
    )

    customer_id = Column(
        Integer,
        ForeignKey("customers.customer_id"),
        nullable=False
    )

    contact = Column(
        String(30),
        nullable=False
    )

    day = Column(
        Integer,
        nullable=False
    )

    month = Column(
        String(20),
        nullable=False
    )

    campaign = Column(
        Integer,
        nullable=False
    )

    pdays = Column(
        Integer,
        nullable=False
    )

    previous = Column(
        Integer,
        nullable=False
    )

    poutcome = Column(
        String(30),
        nullable=False
    )

    created_at = Column(
        DateTime,
        default=datetime.utcnow,
        nullable=False
    )

    updated_at = Column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=False
    )

    customer = relationship(
        "Customer",
        back_populates="campaign_history"
    )


# ============================================================
# 5. NEW CUSTOMER PREDICTIONS
# ============================================================

class Prediction(Base):
    __tablename__ = "predictions"

    prediction_id = Column(
        Integer,
        primary_key=True,
        index=True
    )

    customer_id = Column(
        Integer,
        ForeignKey("customers.customer_id"),
        nullable=False
    )

    prediction = Column(
        String(10),
        nullable=False
    )

    probability = Column(
        Float,
        nullable=False
    )

    model_version = Column(
        String(50),
        nullable=True
    )

    predicted_at = Column(
        DateTime,
        default=datetime.utcnow,
        nullable=False
    )

    customer = relationship(
        "Customer",
        back_populates="predictions"
    )
