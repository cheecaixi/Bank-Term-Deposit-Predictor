from typing import Literal

from pydantic import BaseModel


class CustomerData(BaseModel):
    """
    Customer information required for prediction.
    """

    age: int
    job: Literal[
        "admin.", "blue-collar", "entrepreneur", "housemaid",
        "management", "retired", "self-employed", "services",
        "student", "technician", "unemployed", "unknown"
    ]
    marital: Literal["married", "single", "divorced"]
    education: Literal["primary", "secondary", "tertiary", "unknown"]
    default: Literal["yes", "no"]
    balance: float
    housing: Literal["yes", "no"]
    loan: Literal["yes", "no"]
    contact: Literal["cellular", "telephone", "unknown"]
    day: int
    month: Literal[
        "jan", "feb", "mar", "apr", "may", "jun",
        "jul", "aug", "sep", "oct", "nov", "dec"
    ]
    campaign: int
    pdays: int
    previous: int
    poutcome: Literal["failure", "other", "success", "unknown"]