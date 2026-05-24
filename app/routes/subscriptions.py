from fastapi import APIRouter, Depends

from app.core.dependencies import require_roles
from app.database import get_database
from app.models import collections as C
from app.schemas.subscription import (
    SubscriptionSubscribeRequest,
    SubscriptionVerifyRequest,
)
from app.services.subscription_service import SubscriptionService
from app.utils.helpers import serialize_doc, serialize_docs

router = APIRouter(prefix="/subscriptions", tags=["Subscriptions"])


@router.get("/plans")
async def list_plans():
    """Public list of active seller plans (Basic, Standard, Premium)."""
    database = get_database()
    cursor = database[C.SELLER_PLANS].find({"isActive": True}).sort("weeklyFee", 1)
    plans = serialize_docs(await cursor.to_list(length=20))
    for p in plans:
        name = (p.get("planName") or "").lower()
        p["planKey"] = "advanced" if name == "premium" else name
    return plans


@router.get("/my")
async def my_subscription(user: dict = Depends(require_roles(["seller"]))):
    """Current seller subscription with plan details."""
    sub = await SubscriptionService.get_active_subscription(user["id"])
    if not sub:
        return None
    database = get_database()
    plan = await database[C.SELLER_PLANS].find_one({"_id": sub["planId"]})
    data = serialize_doc(dict(sub))
    data["plan"] = serialize_doc(plan) if plan else None
    if data.get("plan"):
        name = (data["plan"].get("planName") or "").lower()
        data["plan"]["planKey"] = "advanced" if name == "premium" else name
    return data


@router.post("/subscribe")
async def subscribe_to_plan(
    data: SubscriptionSubscribeRequest,
    user: dict = Depends(require_roles(["seller"])),
):
    """
    Seller: start subscription for Basic, Standard, or Premium (advanced).

    Send either `planId` (MongoDB id) or `planKey`: basic | standard | premium | advanced.

    Returns Razorpay checkout details. After payment, call POST /subscriptions/verify.
    """
    return await SubscriptionService.initiate_subscription(
        user, plan_id=data.planId, plan_key=data.planKey
    )


@router.post("/purchase")
async def purchase_plan(
    data: SubscriptionSubscribeRequest,
    user: dict = Depends(require_roles(["seller"])),
):
    """Alias for POST /subscriptions/subscribe."""
    return await SubscriptionService.initiate_subscription(
        user, plan_id=data.planId, plan_key=data.planKey
    )


@router.post("/verify")
async def verify_subscription(
    data: SubscriptionVerifyRequest,
    user: dict = Depends(require_roles(["seller"])),
):
    """Seller: verify Razorpay payment and activate weekly subscription."""
    return await SubscriptionService.complete_subscription(
        user["id"],
        data.razorpay_order_id,
        data.razorpay_payment_id,
        data.razorpay_signature,
        data.planId,
    )
