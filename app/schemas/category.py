from typing import Optional

from pydantic import BaseModel, Field


class CategoryCreateRequest(BaseModel):
    name: str = Field(min_length=2, max_length=100)
    description: Optional[str] = None
    image: Optional[str] = None


class CategoryUpdateRequest(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    image: Optional[str] = None
