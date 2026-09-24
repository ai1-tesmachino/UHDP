from datetime import UTC
from datetime import datetime
from uuid import uuid4

from pydantic import BaseModel
from pydantic import Field


class Task(BaseModel):
    id: str = Field(
        default_factory=lambda: str(uuid4())
    )

    name: str

    status: str = "pending"

    created_at: datetime = Field(
        default_factory=lambda: datetime.now(
            UTC
        )
    )