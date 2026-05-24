from typing import Optional

from pydantic import BaseModel, Field, model_validator

from app.schemas.address import ShippingAddressSchema


class CheckoutRequest(BaseModel):
    shippingAddress: Optional[ShippingAddressSchema] = None
    useSavedAddress: bool = False
    saveAddress: bool = True

    @model_validator(mode="after")
    def address_source(self):
        if not self.useSavedAddress and not self.shippingAddress:
            raise ValueError("Provide shippingAddress or set useSavedAddress to true")
        return self


class OrderStatusUpdateRequest(BaseModel):
    orderStatus: str


class SellerOrderActionRequest(BaseModel):
    action: str  # confirm | reject
