from fastapi import FastAPI

from app.database import Base, engine
from app.routers import router


# Create tables if they do not exist
Base.metadata.create_all(
    bind=engine
)


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