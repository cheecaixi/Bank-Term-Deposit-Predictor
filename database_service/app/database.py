"""Set up connection between database_service and PostgreSQL """
"""Provide database sessions for API requests"""

import os

# Loads configuration values from a local .env file.
from dotenv import load_dotenv
# SQLAlchemy tools for connecting to PostgreSQL and defining ORM models.
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

# Make variables from .env available through os.getenv().
load_dotenv()

# 1. Get the database connection address provided by Docker Compose.
# If the service runs without Docker, use the local PostgreSQL address instead.
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql+psycopg2://postgres:postgres@localhost:5432/bank_marketing"
)

# 2. Create a connection manager that lets the Database Service
# communicate with the PostgreSQL database specified by DATABASE_URL.
engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True
)

# 3. Create database sessions so API requests can read and change data.
SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine
)

# Create the base used to define our database tables.
# Base helps SQLAlchemy recognize which Python classes represent database tables.
Base = declarative_base()

# 4. This function gives each API request its own database session and closes it when finished.
def get_db():
    """Provide one database session to a request and always close it afterward."""
    db = SessionLocal()

    try:
        yield db # Give the session to the API function.
    finally:
        db.close()  # Always close the session after the request finishes.
