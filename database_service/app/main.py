# Main entry point for the Database Service.
# Initializes and updates the database, configures the FastAPI application,
# registers API routes, and provides service and health-check endpoints.

from fastapi import FastAPI
from sqlalchemy import text

from app.database import Base, engine
from app.routers import router


# Build any missing tables from the SQLAlchemy models during service startup.
Base.metadata.create_all(
    bind=engine
)

# Update older versions of the batch_uploads table with missing columns,
# while keeping the existing data.
with engine.begin() as connection:

    # Add a file_hash column to store the SHA-256 hash of each uploaded file.
    # This hash is used to identify duplicate file uploads.
    # IF NOT EXISTS prevents an error if the column has already been created
    connection.execute(text(
        "ALTER TABLE batch_uploads "
        "ADD COLUMN IF NOT EXISTS file_hash VARCHAR(64)"
    ))

    # Check whether the old 'content_hash' column exists.
    # If it exists, copy its existing values into the new 'file_hash' column
    # so that previously stored hashes are not lost.
    connection.execute(text(
        "DO $$ BEGIN "
        "IF EXISTS (SELECT 1 FROM information_schema.columns "
        "WHERE table_name = 'batch_uploads' AND column_name = 'content_hash') "
        "THEN UPDATE batch_uploads SET file_hash = content_hash "
        "WHERE file_hash IS NULL; END IF; END $$"
    ))

    # Create a UNIQUE index on file_hash.
    # This prevents the same file hash from being stored more than once,
    # helping to prevent duplicate CSV uploads.
    connection.execute(text(
        "CREATE UNIQUE INDEX IF NOT EXISTS ix_batch_uploads_file_hash "
        "ON batch_uploads (file_hash)"
    ))

    # Add a status column to track the processing state of each batch.
    # New batches start as 'pending' by default.
    # Possible states used here: pending, processing, completed.
    connection.execute(text(
        "ALTER TABLE batch_uploads "
        "ADD COLUMN IF NOT EXISTS status VARCHAR(20) "
        "NOT NULL DEFAULT 'pending'"
    ))

    # Add created_at to record when each batch upload was created.
    # PostgreSQL automatically uses the current time if no value is provided.
    connection.execute(text(
        "ALTER TABLE batch_uploads "
        "ADD COLUMN IF NOT EXISTS created_at TIMESTAMP "
        "NOT NULL DEFAULT CURRENT_TIMESTAMP"
    ))

      # Update the status of all existing batch uploads based on their progress.
    connection.execute(text(
        # For each batch, determine whether it is completed, processing, or still pending.
        "UPDATE batch_uploads AS batch SET status = CASE "

        # Count how many predictions belong to customers in this batch.
        # If the prediction count is equal to or greater than total_records,
        # the whole batch has been processed.
        "WHEN (SELECT COUNT(*) FROM predictions AS prediction "
        "JOIN customers AS customer "
        "ON customer.customer_id = prediction.customer_id "
        "WHERE customer.batch_id = batch.batch_id) >= batch.total_records "
        "AND batch.total_records > 0 THEN 'completed' "

        # PROCESSING:
        # If customers from this batch already exist but predictions are
        # not complete yet, the batch is still being processed.
        "WHEN EXISTS (SELECT 1 FROM customers AS customer "
        "WHERE customer.batch_id = batch.batch_id) THEN 'processing' "

        "ELSE 'pending' END"
    ))

# Create the FastAPI application for the Database Service.
# The information below is also displayed in the automatic API documentation.
app = FastAPI(
    title="Bank Term Deposit Database Service",
    description="Database microservice for customer, campaign and prediction data",
    version="1.0.0"
)

# Register the API router with the FastAPI application.
# This makes all endpoints defined inside the router accessible through this service.
app.include_router(router)

# Root endpoint used to confirm that the Database Service is running.
@app.get("/")
def root():
    """Return basic service identity information for users and tools."""
    return {
        "service": "database-service",
        "status": "running"
    }

# Health-check endpoint used by monitoring services to check
# whether the Database Service is available and healthy.
@app.get("/health")
def health():
    """Provide the lightweight health endpoint used by service monitoring."""
    return {
        "status": "healthy"
    }
