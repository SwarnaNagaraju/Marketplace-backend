from typing import Optional

from pydantic import BaseModel, Field


class QuotaRequestCreate(BaseModel):
    requestedExtraUploads: int = Field(gt=0, le=500)
    reason: str = Field(min_length=5, max_length=500)


class QuotaAdminAction(BaseModel):
    action: str  # approve | reject
    adminMessage: Optional[str] = None
