"""SQLAlchemy table models and relationships for persisted application data."""

from datetime import datetime

# Import SQLAlchemy column types and database constraints.
from sqlalchemy import (
    Column,
    Integer,
    String,
    Float,
    DateTime,
    ForeignKey
)

# relationship() defines how SQLAlchemy models are connected
# and allows related records to be accessed through Python objects.
from sqlalchemy.orm import relationship

# Base is inherited by every SQLAlchemy model so that
# SQLAlchemy can map these Python classes to database tables.
from app.database import Base


# ============================================================
# 1. BATCH UPLOADS - Stores information about each uploaded CSV batch.
# ============================================================

class BatchUpload(Base):
    """Track a unique CSV upload and the progress of its predictions."""

    # Name of the table created/used in PostgreSQL.
    __tablename__ = "batch_uploads"

     # Primary key that uniquely identifies each uploaded batch.
    batch_id = Column(
        Integer,
        primary_key=True,
        index=True
    )
    # Original name of the uploaded CSV file.
    file_name = Column(
        String(255),
        nullable=False
    )

    # Number of customer records contained in the uploaded CSV.
    # Used later to determine whether the whole batch is completed.
    total_records = Column(
        Integer,
        nullable=False
    )

    # SHA-256 hash of the uploaded CSV file.
    # The hash is unique, allowing the system to detect and
    # prevent the same file from being uploaded multiple times.
    file_hash = Column(
        String(64),
        nullable=False,
        unique=True,
        index=True
    )
     # Tracks the processing progress of the batch:
    # pending -> processing -> completed.
    status = Column(
        String(20),
        default="pending",
        nullable=False
    )

    # Records when the batch database record was created.
    created_at = Column(
        DateTime,
        default=datetime.utcnow,
        nullable=False
    )

    # Records when the CSV batch was uploaded.
    uploaded_at = Column(
        DateTime,
        default=datetime.utcnow,
        nullable=False
    )

    # One-to-many relationship:
    # One BatchUpload can contain many Customer records.
    customers = relationship(
        "Customer",
        back_populates="batch"
    )


# ============================================================
# 2. CUSTOMERS -  Stores customer profile information used by the AI model.
# ============================================================

class Customer(Base):
    """Store a customer's profile and link it to campaigns and predictions."""

    __tablename__ = "customers"

    # Primary key that uniquely identifies each customer.
    customer_id = Column(
        Integer,
        primary_key=True,
        index=True
    )

    # Phone number acts as a unique customer identifier
    # to prevent duplicate customer records.
    phone_number = Column(
        String(20),
        unique=True,
        nullable=False,
        index=True
    )

    # Foreign key linking a customer to the CSV batch it came from.
    # NULL means the customer was entered manually instead of by CSV upload.
    batch_id = Column(
        Integer,
        ForeignKey("batch_uploads.batch_id"),
        nullable=True
    )

    # Customer demographic and financial features used for prediction.
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

    # Tracks whether an AI prediction has been generated for this customer.
    # PENDING = waiting for prediction
    # COMPLETED = prediction has been generated
    prediction_status = Column(
        String(20),
        default="PENDING",
        nullable=False
    )

    # Automatically records when the customer was first created.
    created_at = Column(
        DateTime,
        default=datetime.utcnow,
        nullable=False
    )

    # Records the last update time.
    # onupdate automatically changes the timestamp when the record is updated.
    updated_at = Column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=False
    )

    # Many-to-one relationship:
    # Each customer can belong to one uploaded batch.
    batch = relationship(
        "BatchUpload",
        back_populates="customers"
    )

    # One-to-many relationship:
    # One customer can have multiple campaign-history records.
    # cascade="all, delete-orphan" means related campaign records
    # are also removed if they no longer belong to a customer.
    campaign_history = relationship(
        "CampaignHistory",
        back_populates="customer",
        cascade="all, delete-orphan"
    )

    # One-to-many relationship:
    # One customer can have multiple prediction records.
    predictions = relationship(
        "Prediction",
        back_populates="customer",
        cascade="all, delete-orphan"
    )


# ============================================================
# 3. CAMPAIGN HISTORY -  Stores marketing/contact information used for prediction.
# ============================================================

class CampaignHistory(Base):
    """Store marketing-contact features supplied for a customer prediction."""

    __tablename__ = "campaign_history"

    # Primary key that uniquely identifies each campaign record.
    campaign_id = Column(
        Integer,
        primary_key=True,
        index=True
    )
    # Foreign key linking this campaign record to a customer.
    customer_id = Column(
        Integer,
        ForeignKey("customers.customer_id"),
        nullable=False
    )
     # Marketing campaign features used by the prediction model.
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
    # Number of contacts performed during the current campaign.
    campaign = Column(
        Integer,
        nullable=False
    )
    # Number of days since the customer was previously contacted.
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
    # Automatically records when this campaign record was last updated
    updated_at = Column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=False
    )
    # Many-to-one relationship:
    # Each campaign-history record belongs to one customer.
    customer = relationship(
        "Customer",
        back_populates="campaign_history"
    )


# ============================================================
# 4. NEW CUSTOMER PREDICTIONS - Stores prediction results returned by the AI model.
# ============================================================

class Prediction(Base):
    """Store an AI prediction result generated for a customer."""

    __tablename__ = "predictions"

    # Primary key that uniquely identifies each prediction.
    prediction_id = Column(
        Integer,
        primary_key=True,
        index=True
    )
    # Foreign key linking the prediction result to its customer.
    customer_id = Column(
        Integer,
        ForeignKey("customers.customer_id"),
        nullable=False
    )
    # Final prediction result, such as "yes" or "no"
    # for term-deposit subscription.
    prediction = Column(
        String(10),
        nullable=False
    )
     # Confidence/probability returned by the AI model.
    probability = Column(
        Float,
        nullable=False
    )
    # Records which version of the AI model produced the prediction.
    # Nullable because older predictions may not contain version information
    model_version = Column(
        String(50),
        nullable=True
    )

    # Automatically records when the prediction was generated.
    predicted_at = Column(
        DateTime,
        default=datetime.utcnow,
        nullable=False
    )
    # Many-to-one relationship:
    # Each prediction belongs to one customer.
    customer = relationship(
        "Customer",
        back_populates="predictions"
    )
