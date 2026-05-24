from pydantic import BaseModel, Field


class ReviewCreateRequest(BaseModel):
    productId: str
    rating: int = Field(ge=1, le=5)
    reviewText: str = Field(min_length=3, max_length=1000)
