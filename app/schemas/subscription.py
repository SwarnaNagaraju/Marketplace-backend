from typing import Literal, Optional

from pydantic import BaseModel, Field, model_validator


class PlanCreateRequest(BaseModel):
    planName: str
    weeklyFee: float = Field(gt=0)
    productUploadLimit: int = Field(gt=0)
    extraUploadPrice: float = Field(ge=0)
    features: list[str] = []
    isActive: bool = True


class PlanUpdateRequest(BaseModel):
    planName: Optional[str] = None
    weeklyFee: Optional[float] = Field(default=None, gt=0)
    productUploadLimit: Optional[int] = Field(default=None, gt=0)
    extraUploadPrice: Optional[float] = None
    features: Optional[list[str]] = None
    isActive: Optional[bool] = None


class SubscriptionPurchaseRequest(BaseModel):
    planId: str


PlanKey = Literal["basic", "standard", "premium", "advanced"]


class SubscriptionSubscribeRequest(BaseModel):
    """Subscribe to a weekly plan by MongoDB id or slug (basic / standard / premium / advanced)."""

    planId: Optional[str] = None
    planKey: Optional[PlanKey] = None

    @model_validator(mode="after")
    def require_plan_selector(self):
        if not self.planId and not self.planKey:
            raise ValueError("Provide planId or planKey (basic, standard, premium, advanced)")
        return self


class SubscriptionVerifyRequest(BaseModel):
    razorpay_order_id: str
    razorpay_payment_id: str
    razorpay_signature: str
    planId: str
