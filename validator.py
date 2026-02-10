from pydantic import BaseModel, Field
from typing import Literal


class ClassificationResponse(BaseModel):
    intent: Literal["COMPLAINT"]

    department: Literal[
        "SANITATION",
        "WATER",
        "ELECTRICITY",
        "ROADS",
        "PUBLIC_SAFETY",
        "OTHER"
    ]

    priority: Literal["LOW", "MEDIUM", "HIGH"]

    confidence: float = Field(ge=0.0, le=1.0)
