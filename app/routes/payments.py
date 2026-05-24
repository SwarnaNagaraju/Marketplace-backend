from fastapi import APIRouter, Depends

from app.config.settings import get_settings
from app.core.dependencies import get_current_user
from app.schemas.payment import PaymentCreateOrderRequest, PaymentVerifyRequest
from app.services.payment_service import PaymentService

router = APIRouter(prefix="/payments", tags=["Payments"])


@router.post("/create-order")
async def create_order(data: PaymentCreateOrderRequest, user: dict = Depends(get_current_user)):
    result = await PaymentService.create_payment_order(
        user["id"],
        data.paymentType,
        data.amount,
        data.planId,
        data.quotaRequestId,
        data.orderIds,
    )
    result["key"] = get_settings().razorpay_key_id
    return result


@router.post("/verify")
async def verify_payment(data: PaymentVerifyRequest, user: dict = Depends(get_current_user)):
    return await PaymentService.verify_and_fulfill(
        user["id"],
        data.razorpay_order_id,
        data.razorpay_payment_id,
        data.razorpay_signature,
        data.paymentType,
        data.planId,
        data.quotaRequestId,
        data.orderIds,
    )
