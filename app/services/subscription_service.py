import re
from datetime import timedelta, timezone

from app.config.settings import get_settings
from app.core.exceptions import bad_request, forbidden
from app.database import get_database
from app.models import collections as C
from app.utils.helpers import oid, serialize_doc, utc_now

# Slug aliases for seeded plan names
PLAN_KEY_ALIASES: dict[str, str] = {
    "basic": "Basic",
    "standard": "Standard",
    "premium": "Premium",
    "advanced": "Premium",
}


class SubscriptionService:
    @staticmethod
    async def resolve_plan(
        plan_id: str | None = None,
        plan_key: str | None = None
    ) -> dict:

        database = get_database()

        if plan_id:
            plan = await database[C.SELLER_PLANS].find_one(
                {
                    "_id": oid(plan_id),
                    "isActive": True
                }
            )

            if not plan:
                raise bad_request("Plan not found or inactive")

            return plan

        if not plan_key:
            raise bad_request("planId or planKey is required")

        key = plan_key.lower().strip()

        plan_name = PLAN_KEY_ALIASES.get(key)

        if not plan_name:
            raise bad_request(
                "Invalid planKey. Use: basic, standard, premium, or advanced"
            )

        plan = await database[C.SELLER_PLANS].find_one(
            {
                "planName": {
                    "$regex": f"^{re.escape(plan_name)}$",
                    "$options": "i"
                },
                "isActive": True
            }
        )

        if not plan:
            raise bad_request(f"Plan '{plan_name}' is not available")

        return plan

    @staticmethod
    async def initiate_subscription(
        seller: dict,
        plan_id: str | None = None,
        plan_key: str | None = None
    ) -> dict:

        if seller.get("isBlocked"):
            raise forbidden("Seller account is blocked")

        plan = await SubscriptionService.resolve_plan(
            plan_id,
            plan_key
        )

        resolved_plan_id = str(plan["_id"])

        from app.services.payment_service import PaymentService

        payment_order = await PaymentService.create_payment_order(
            seller["id"],
            "subscription",
            plan_id=resolved_plan_id,
        )

        settings = get_settings()

        plan_data = serialize_doc(plan)

        return {
            "message": "Complete payment to activate your weekly subscription",
            "plan": plan_data,
            "planId": resolved_plan_id,
            "planKey": plan_key or plan_data.get("planName", "").lower(),
            "weeklyFee": plan["weeklyFee"],
            "uploadLimit": plan["productUploadLimit"],
            "razorpayOrderId": payment_order["razorpayOrderId"],
            "amount": payment_order["amount"],
            "currency": payment_order["currency"],
            "key": settings.razorpay_key_id,
            "paymentType": "subscription",
        }

    @staticmethod
    async def complete_subscription(
        seller_id: str,
        razorpay_order_id: str,
        razorpay_payment_id: str,
        razorpay_signature: str,
        plan_id: str,
    ) -> dict:

        from app.services.payment_service import PaymentService

        payment = await PaymentService.verify_and_fulfill(
            seller_id,
            razorpay_order_id,
            razorpay_payment_id,
            razorpay_signature,
            "subscription",
            plan_id=plan_id,
        )

        sub = await SubscriptionService.get_active_subscription(
            seller_id
        )

        database = get_database()

        plan = await database[C.SELLER_PLANS].find_one(
            {"_id": oid(plan_id)}
        )

        return {
            "payment": payment,
            "subscription": serialize_doc(dict(sub)) if sub else None,
            "plan": serialize_doc(plan) if plan else None,
        }

    @staticmethod
    async def get_active_subscription(
        seller_id: str
    ) -> dict | None:

        database = get_database()

        sub = await database[C.SELLER_SUBSCRIPTIONS].find_one(
            {
                "sellerId": oid(seller_id),
                "status": "active"
            },
            sort=[("createdAt", -1)],
        )

        if not sub:
            return None

        now = utc_now()

        expiry = sub.get("expiryDate")

        if expiry:

            # Convert expiry to timezone-aware UTC
            if expiry.tzinfo is None:
                expiry = expiry.replace(tzinfo=timezone.utc)

            # Convert now to timezone-aware UTC
            if now.tzinfo is None:
                now = now.replace(tzinfo=timezone.utc)

            # Check expiry
            if expiry < now:

                await database[C.SELLER_SUBSCRIPTIONS].update_one(
                    {"_id": sub["_id"]},
                    {
                        "$set": {
                            "isExpired": True,
                            "status": "expired",
                            "updatedAt": now,
                        }
                    },
                )

                return None

        return sub

    @staticmethod
    async def ensure_active(seller_id: str) -> dict:

        sub = await SubscriptionService.get_active_subscription(
            seller_id
        )

        if not sub:
            raise forbidden(
                "No active subscription. Please renew your weekly plan."
            )

        return sub

    @staticmethod
    async def validate_upload_eligibility(
        seller: dict
    ) -> dict:

        if seller.get("role") != "seller":
            raise forbidden("Seller role required")

        if seller.get("isBlocked"):
            raise forbidden("Seller account is blocked by admin")

        sub = await SubscriptionService.ensure_active(
            seller["id"]
        )

        if sub.get("remainingUploads", 0) <= 0:
            raise forbidden(
                "Upload quota exceeded. Request extra quota or upgrade plan."
            )

        return sub

    @staticmethod
    async def consume_upload(seller_id: str) -> None:

        sub = await SubscriptionService.ensure_active(
            seller_id
        )

        database = get_database()

        result = await database[C.SELLER_SUBSCRIPTIONS].update_one(
            {
                "_id": sub["_id"],
                "remainingUploads": {"$gt": 0}
            },
            {
                "$inc": {
                    "usedUploads": 1,
                    "remainingUploads": -1
                },
                "$set": {
                    "updatedAt": utc_now()
                },
            },
        )

        if result.modified_count == 0:
            raise forbidden("Upload quota exceeded")

    @staticmethod
    async def activate_subscription(
        seller_id: str,
        plan_id: str,
        payment_id: str
    ) -> dict:

        database = get_database()

        plan = await database[C.SELLER_PLANS].find_one(
            {
                "_id": oid(plan_id),
                "isActive": True
            }
        )

        if not plan:
            raise bad_request("Invalid plan")

        now = utc_now()

        if now.tzinfo is None:
            now = now.replace(tzinfo=timezone.utc)

        expiry = now + timedelta(days=7)

        limit = plan["productUploadLimit"]

        existing = await SubscriptionService.get_active_subscription(
            seller_id
        )

        if existing:

            await database[C.SELLER_SUBSCRIPTIONS].update_one(
                {"_id": existing["_id"]},
                {
                    "$set": {
                        "planId": oid(plan_id),
                        "paymentId": oid(payment_id),
                        "uploadLimit": limit,
                        "usedUploads": 0,
                        "remainingUploads": limit,
                        "startDate": now,
                        "expiryDate": expiry,
                        "isExpired": False,
                        "status": "active",
                        "updatedAt": now,
                    }
                },
            )

            doc = await database[C.SELLER_SUBSCRIPTIONS].find_one(
                {"_id": existing["_id"]}
            )

        else:

            doc = {
                "sellerId": oid(seller_id),
                "planId": oid(plan_id),
                "paymentId": oid(payment_id),
                "uploadLimit": limit,
                "usedUploads": 0,
                "remainingUploads": limit,
                "extraUploadsPurchased": 0,
                "startDate": now,
                "expiryDate": expiry,
                "isExpired": False,
                "status": "active",
                "createdAt": now,
                "updatedAt": now,
            }

            result = await database[C.SELLER_SUBSCRIPTIONS].insert_one(doc)

            doc["_id"] = result.inserted_id

        return serialize_doc(doc)

    @staticmethod
    async def add_quota(
        seller_id: str,
        extra: int
    ) -> None:

        sub = await SubscriptionService.ensure_active(
            seller_id
        )

        database = get_database()

        await database[C.SELLER_SUBSCRIPTIONS].update_one(
            {"_id": sub["_id"]},
            {
                "$inc": {
                    "remainingUploads": extra,
                    "uploadLimit": extra,
                    "extraUploadsPurchased": extra,
                },
                "$set": {
                    "updatedAt": utc_now()
                },
            },
        )