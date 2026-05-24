import uuid

from app.core.exceptions import bad_request
from app.database import get_database
from app.models import collections as C
from app.services.notification_service import create_notification
from app.services.subscription_service import SubscriptionService
from app.utils.helpers import oid, serialize_doc, utc_now
from app.utils.razorpay_client import create_razorpay_order, verify_payment_signature


class PaymentService:
    @staticmethod
    async def create_payment_order(
        user_id: str,
        payment_type: str,
        amount: float | None = None,
        plan_id: str | None = None,
        quota_request_id: str | None = None,
        order_ids: list[str] | None = None,
    ) -> dict:
        database = get_database()
        computed_amount = amount

        if payment_type == "subscription":
            if not plan_id:
                raise bad_request("planId required")
            plan = await database[C.SELLER_PLANS].find_one({"_id": oid(plan_id)})
            if not plan:
                raise bad_request("Plan not found")
            computed_amount = plan["weeklyFee"]
        elif payment_type == "quota_upgrade":
            if not quota_request_id:
                raise bad_request("quotaRequestId required")
            qr = await database[C.QUOTA_REQUESTS].find_one({"_id": oid(quota_request_id)})
            if not qr or str(qr["sellerId"]) != user_id:
                raise bad_request("Quota request not found")
            computed_amount = qr["extraFee"]
        elif payment_type == "order":
            if not order_ids:
                raise bad_request("orderIds required")
            total = 0
            for oid_str in order_ids:
                order = await database[C.ORDERS].find_one({"_id": oid(oid_str), "customerId": oid(user_id)})
                if not order:
                    raise bad_request(f"Order {oid_str} not found")
                total += order["finalAmount"]
            computed_amount = total
        else:
            raise bad_request("Invalid payment type")

        if not computed_amount or computed_amount <= 0:
            raise bad_request("Invalid amount")

        amount_paise = int(computed_amount * 100)
        receipt = f"{payment_type}_{uuid.uuid4().hex[:12]}"
        rz_order = create_razorpay_order(
            amount_paise,
            receipt,
            notes={
                "paymentType": payment_type,
                "userId": user_id,
                "planId": plan_id or "",
                "quotaRequestId": quota_request_id or "",
                "orderIds": ",".join(order_ids or []),
            },
        )
        return {
            "razorpayOrderId": rz_order["id"],
            "amount": computed_amount,
            "currency": "INR",
            "key": None,
            "paymentType": payment_type,
            "planId": plan_id,
            "quotaRequestId": quota_request_id,
            "orderIds": order_ids,
        }

    @staticmethod
    async def verify_and_fulfill(
        user_id: str,
        razorpay_order_id: str,
        razorpay_payment_id: str,
        razorpay_signature: str,
        payment_type: str,
        plan_id: str | None = None,
        quota_request_id: str | None = None,
        order_ids: list[str] | None = None,
    ) -> dict:
        if not verify_payment_signature(razorpay_order_id, razorpay_payment_id, razorpay_signature):
            raise bad_request("Payment verification failed")

        database = get_database()
        existing = await database[C.PAYMENTS].find_one({"razorpayPaymentId": razorpay_payment_id})
        if existing:
            return serialize_doc(existing)

        amount = 0
        if payment_type == "subscription" and plan_id:
            plan = await database[C.SELLER_PLANS].find_one({"_id": oid(plan_id)})
            amount = plan["weeklyFee"] if plan else 0
        elif payment_type == "quota_upgrade" and quota_request_id:
            qr = await database[C.QUOTA_REQUESTS].find_one({"_id": oid(quota_request_id)})
            amount = qr["extraFee"] if qr else 0
        elif payment_type == "order" and order_ids:
            for oid_str in order_ids:
                order = await database[C.ORDERS].find_one({"_id": oid(oid_str)})
                if order:
                    amount += order["finalAmount"]

        payment_doc = {
            "userId": oid(user_id),
            "orderId": oid(order_ids[0]) if order_ids else None,
            "paymentType": payment_type,
            "razorpayOrderId": razorpay_order_id,
            "razorpayPaymentId": razorpay_payment_id,
            "razorpaySignature": razorpay_signature,
            "amount": amount,
            "currency": "INR",
            "paymentMethod": "razorpay",
            "status": "paid",
            "paidAt": utc_now(),
            "createdAt": utc_now(),
            "metadata": {"orderIds": order_ids or [], "planId": plan_id, "quotaRequestId": quota_request_id},
        }
        result = await database[C.PAYMENTS].insert_one(payment_doc)
        payment_id = str(result.inserted_id)

        if payment_type == "subscription" and plan_id:
            await SubscriptionService.activate_subscription(user_id, plan_id, payment_id)
            await create_notification(
                user_id, "Subscription Active", "Your weekly plan is now active.", "subscription"
            )
        elif payment_type == "quota_upgrade" and quota_request_id:
            await database[C.QUOTA_REQUESTS].update_one(
                {"_id": oid(quota_request_id)},
                {"$set": {"paymentId": oid(payment_id), "paymentStatus": "paid"}},
            )
            await create_notification(
                user_id, "Quota Payment Received", "Awaiting admin approval.", "payment"
            )
        elif payment_type == "order" and order_ids:
            now = utc_now()
            for oid_str in order_ids:
                await database[C.ORDERS].update_one(
                    {"_id": oid(oid_str)},
                    {
                        "$set": {
                            "paymentStatus": "paid",
                            "orderStatus": "confirmed",
                            "paymentId": oid(payment_id),
                            "updatedAt": now,
                        }
                    },
                )
                order = await database[C.ORDERS].find_one({"_id": oid(oid_str)})
                if order:
                    await create_notification(
                        str(order["customerId"]),
                        "Payment Successful",
                        f"Order {order.get('orderNumber')} confirmed.",
                        "order",
                    )
                    await create_notification(
                        str(order["sellerId"]),
                        "New Order",
                        f"Order {order.get('orderNumber')} received.",
                        "order",
                    )

        payment_doc["_id"] = result.inserted_id
        return serialize_doc(payment_doc)
