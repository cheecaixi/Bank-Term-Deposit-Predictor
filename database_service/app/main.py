from fastapi import FastAPI
from sqlalchemy import text

from app.database import Base, engine
from app.routers import router


# Create tables if they do not exist
Base.metadata.create_all(
    bind=engine
)

# create_all does not add columns to an existing table, so migrate old local
# databases without deleting their batch history.
with engine.begin() as connection:
    connection.execute(text(
        "ALTER TABLE batch_uploads "
        "ADD COLUMN IF NOT EXISTS file_hash VARCHAR(64)"
    ))
    connection.execute(text(
        "DO $$ BEGIN "
        "IF EXISTS (SELECT 1 FROM information_schema.columns "
        "WHERE table_name = 'batch_uploads' AND column_name = 'content_hash') "
        "THEN UPDATE batch_uploads SET file_hash = content_hash "
        "WHERE file_hash IS NULL; END IF; END $$"
    ))
    connection.execute(text(
        "CREATE UNIQUE INDEX IF NOT EXISTS ix_batch_uploads_file_hash "
        "ON batch_uploads (file_hash)"
    ))
    connection.execute(text(
        "ALTER TABLE batch_uploads "
        "ADD COLUMN IF NOT EXISTS status VARCHAR(20) "
        "NOT NULL DEFAULT 'pending'"
    ))
    connection.execute(text(
        "ALTER TABLE batch_uploads "
        "ADD COLUMN IF NOT EXISTS created_at TIMESTAMP "
        "NOT NULL DEFAULT CURRENT_TIMESTAMP"
    ))
    connection.execute(text(
        "UPDATE batch_uploads AS batch SET status = CASE "
        "WHEN (SELECT COUNT(*) FROM predictions AS prediction "
        "JOIN customers AS customer "
        "ON customer.customer_id = prediction.customer_id "
        "WHERE customer.batch_id = batch.batch_id) >= batch.total_records "
        "AND batch.total_records > 0 THEN 'completed' "
        "WHEN EXISTS (SELECT 1 FROM customers AS customer "
        "WHERE customer.batch_id = batch.batch_id) THEN 'processing' "
        "ELSE 'pending' END"
    ))


app = FastAPI(
    title="Bank Term Deposit Database Service",
    description="Database microservice for customer, campaign and prediction data",
    version="1.0.0"
)


app.include_router(router)


@app.get("/")
def root():
    return {
        "service": "database-service",
        "status": "running"
    }


@app.get("/health")
def health():
    return {
        "status": "healthy"
    }
