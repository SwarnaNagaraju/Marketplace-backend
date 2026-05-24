from fastapi import APIRouter, Depends

from app.core.dependencies import require_roles
from app.database import get_database
from app.models import collections as C
from app.services.subscription_service import SubscriptionService
from app.utils.helpers import oid, serialize_doc

router = APIRouter(prefix="/seller", tags=["Seller"])


@router.get("/analytics")
async def seller_analytics(user: dict = Depends(require_roles(["seller"]))):
    database = get_database()
    seller_oid = oid(user["id"])
    paid_orders = await database[C.ORDERS].find(
        {"sellerId": seller_oid, "paymentStatus": "paid"}
    ).to_list(1000)
    earnings = sum(o.get("finalAmount", 0) for o in paid_orders)
    pending = await database[C.ORDERS].count_documents(
        {"sellerId": seller_oid, "orderStatus": {"$in": ["confirmed", "processing"]}}
    )
    sub = await SubscriptionService.get_active_subscription(user["id"])
    plan = None
    if sub:
        plan = await database[C.SELLER_PLANS].find_one({"_id": sub["planId"]})
    return {
        "earnings": round(earnings, 2),
        "totalOrders": len(paid_orders),
        "pendingOrders": pending,
        "subscription": serialize_doc(sub) if sub else None,
        "plan": serialize_doc(plan) if plan else None,
    }
