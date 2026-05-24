from app.core.exceptions import bad_request, forbidden, not_found
from app.database import get_database
from app.models import collections as C
from app.schemas.quota import QuotaRequestCreate
from app.services.subscription_service import SubscriptionService
from app.utils.helpers import oid, serialize_doc, serialize_docs, utc_now


class QuotaService:
    @staticmethod
    async def create_request(seller: dict, data: QuotaRequestCreate) -> dict:
        if seller.get("role") != "seller":
            raise forbidden("Seller only")
        sub = await SubscriptionService.get_active_subscription(seller["id"])
        if not sub:
            raise bad_request("Active subscription required")
        database = get_database()
        plan = await database[C.SELLER_PLANS].find_one({"_id": sub["planId"]})
        extra_price = plan.get("extraUploadPrice", 199) if plan else 199
        extra_fee = round(extra_price * data.requestedExtraUploads / 20, 2)
        if extra_fee < 199:
            extra_fee = 199
        doc = {
            "sellerId": oid(seller["id"]),
            "subscriptionId": sub["_id"],
            "requestedExtraUploads": data.requestedExtraUploads,
            "reason": data.reason,
            "extraFee": extra_fee,
            "paymentId": None,
            "paymentStatus": "pending",
            "adminApprovalStatus": "pending",
            "adminMessage": None,
            "approvedBy": None,
            "approvedAt": None,
            "createdAt": utc_now(),
        }
        result = await database[C.QUOTA_REQUESTS].insert_one(doc)
        doc["_id"] = result.inserted_id
        return serialize_doc(doc)

    @staticmethod
    async def seller_requests(seller_id: str) -> list[dict]:
        database = get_database()
        cursor = database[C.QUOTA_REQUESTS].find({"sellerId": oid(seller_id)}).sort("createdAt", -1)
        return serialize_docs(await cursor.to_list(length=100))

    @staticmethod
    async def admin_action(admin: dict, request_id: str, action: str, message: str | None) -> dict:
        if action not in ("approve", "reject"):
            raise bad_request("action must be approve or reject")
        database = get_database()
        req = await database[C.QUOTA_REQUESTS].find_one({"_id": oid(request_id)})
        if not req:
            raise not_found("Request not found")
        if req.get("paymentStatus") != "paid":
            raise bad_request("Payment not completed")
        if req.get("adminApprovalStatus") != "pending":
            raise bad_request("Already processed")
        now = utc_now()
        status = "approved" if action == "approve" else "rejected"
        await database[C.QUOTA_REQUESTS].update_one(
            {"_id": oid(request_id)},
            {
                "$set": {
                    "adminApprovalStatus": status,
                    "adminMessage": message,
                    "approvedBy": oid(admin["id"]),
                    "approvedAt": now,
                }
            },
        )
        if action == "approve":
            await SubscriptionService.add_quota(
                str(req["sellerId"]), req["requestedExtraUploads"]
            )
        updated = await database[C.QUOTA_REQUESTS].find_one({"_id": oid(request_id)})
        return serialize_doc(updated)

    @staticmethod
    async def pending_requests() -> list[dict]:
        database = get_database()
        cursor = database[C.QUOTA_REQUESTS].find(
            {"adminApprovalStatus": "pending", "paymentStatus": "paid"}
        ).sort("createdAt", -1)
        return serialize_docs(await cursor.to_list(length=100))
