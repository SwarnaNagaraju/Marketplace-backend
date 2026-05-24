from pydantic import BaseModel, Field


class ShippingAddressSchema(BaseModel):
    fullName: str = Field(min_length=2, max_length=100)
    phone: str = Field(min_length=10, max_length=15)
    street: str = Field(min_length=3, max_length=200)
    city: str = Field(min_length=2, max_length=100)
    state: str = Field(min_length=2, max_length=100)
    country: str = Field(default="India", max_length=100)
    pincode: str = Field(min_length=4, max_length=10)
