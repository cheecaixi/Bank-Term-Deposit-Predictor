# schemas.py
# Define the exact customer fields accepted by POST /predict.
# FastAPI uses this model to reject invalid requests automatically.

from typing import Literal

from pydantic import BaseModel


class CustomerData(BaseModel):
    """
    Customer information required for prediction.
    """

    # Customer profile
    age: int
    job: Literal[
        "admin.", "blue-collar", "entrepreneur", "housemaid",
        "management", "retired", "self-employed", "services",
        "student", "technician", "unemployed", "unknown"
    ]
    marital: Literal["married", "single", "divorced"]
    education: Literal["primary", "secondary", "tertiary", "unknown"]

    # Financial and loan information
    default: Literal["yes", "no"]
    balance: float
    housing: Literal["yes", "no"]
    loan: Literal["yes", "no"]

    # Current marketing contact information
    contact: Literal["cellular", "telephone", "unknown"]
    day: int
    month: Literal[
        "jan", "feb", "mar", "apr", "may", "jun",
        "jul", "aug", "sep", "oct", "nov", "dec"
    ]

    # Current and previous campaign history
    campaign: int
    pdays: int
    previous: int
    poutcome: Literal["failure", "other", "success", "unknown"]
