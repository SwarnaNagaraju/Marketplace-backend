from pydantic import BaseModel, Field


class CartAddRequest(BaseModel):
    productId: str
    quantity: int = Field(ge=1, default=1)


class CartUpdateRequest(BaseModel):
    quantity: int = Field(ge=1)
