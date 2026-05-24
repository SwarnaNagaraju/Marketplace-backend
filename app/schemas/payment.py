from typing import Literal, Optional

from pydantic import BaseModel, Field


class PaymentCreateOrderRequest(BaseModel):
    paymentType: Literal["order", "subscription", "quota_upgrade"]
    amount: Optional[float] = None
    planId: Optional[str] = None
    quotaRequestId: Optional[str] = None
    orderIds: Optional[list[str]] = None


class PaymentVerifyRequest(BaseModel):
    razorpay_order_id: str
    razorpay_payment_id: str
    razorpay_signature: str
    paymentType: Literal["order", "subscription", "quota_upgrade"]
    planId: Optional[str] = None
    quotaRequestId: Optional[str] = None
    orderIds: Optional[list[str]] = None
