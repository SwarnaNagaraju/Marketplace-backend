from typing import Optional

from pydantic import BaseModel, Field


class SpecificationsSchema(BaseModel):
    color: Optional[str] = None
    size: Optional[str] = None
    weight: Optional[str] = None


class ProductCreateRequest(BaseModel):
    title: str = Field(min_length=2, max_length=200)
    description: str
    shortDescription: Optional[str] = None
    price: float = Field(gt=0)
    discountPrice: Optional[float] = None
    stock: int = Field(ge=0)
    brand: Optional[str] = None
    images: list[str] = []
    thumbnail: Optional[str] = None
    categoryId: str
    specifications: Optional[SpecificationsSchema] = None


class ProductUpdateRequest(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    shortDescription: Optional[str] = None
    price: Optional[float] = Field(default=None, gt=0)
    discountPrice: Optional[float] = None
    stock: Optional[int] = Field(default=None, ge=0)
    brand: Optional[str] = None
    images: Optional[list[str]] = None
    thumbnail: Optional[str] = None
    categoryId: Optional[str] = None
    specifications: Optional[SpecificationsSchema] = None
    isActive: Optional[bool] = None
