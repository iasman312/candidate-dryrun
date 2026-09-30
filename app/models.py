from datetime import datetime
from enum import Enum

from pydantic import BaseModel, Field


class Status(Enum):
    DRAFT = "draft"
    SUBMITTED = "submitted"
    APPROVED = "approved"
    DECLINED = "declined"
    FUNDED = "funded"


class ApplicationIn(BaseModel):
    business_name: str = Field(min_length=1)
    requested_amount: int = Field(gt=0, description="Whole US dollars")
    lender: str = Field(min_length=1)


class Application(ApplicationIn):
    id: str
    status: Status = Status.DRAFT
    lender_reference: str | None = None
    created_at: datetime
