from app.database import get_database
from app.models import collections as C
from app.utils.helpers import oid, serialize_docs, utc_now


class AdminService:
    @staticmethod
    async def dashboard_stats() -> dict:
        database = get_database()
        customers = await database[C.USERS].count_documents({"role": "customer"})
        sellers = await database[C.USERS].count_documents({"role": "seller"})
        products = await database[C.PRODUCTS].count_documents({"isDeleted": False})
        orders = await database[C.ORDERS].count_documents({})
        paid_orders = await database[C.ORDERS].find({"paymentStatus": "paid"}).to_list(10000)
        revenue = sum(o.get("finalAmount", 0) for o in paid_orders)
        active_subs = await database[C.SELLER_SUBSCRIPTIONS].count_documents(
            {"status": "active", "isExpired": False}
        )
        expired_subs = await database[C.SELLER_SUBSCRIPTIONS].count_documents({"status": "expired"})
        pending_quota = await database[C.QUOTA_REQUESTS].count_documents(
            {"adminApprovalStatus": "pending", "paymentStatus": "paid"}
        )

        top_sellers = await database[C.ORDERS].aggregate(
            [
                {"$match": {"paymentStatus": "paid"}},
                {"$group": {"_id": "$sellerId", "total": {"$sum": "$finalAmount"}, "count": {"$sum": 1}}},
                {"$sort": {"total": -1}},
                {"$limit": 5},
            ]
        ).to_list(5)

        top_products = await database[C.ORDERS].aggregate(
            [
                {"$match": {"paymentStatus": "paid"}},
                {"$unwind": "$products"},
                {"$group": {"_id": "$products.productId", "title": {"$first": "$products.title"}, "sold": {"$sum": "$products.quantity"}}},
                {"$sort": {"sold": -1}},
                {"$limit": 5},
            ]
        ).to_list(5)

        now = utc_now()
        expiring = await database[C.SELLER_SUBSCRIPTIONS].find(
            {
                "status": "active",
                "expiryDate": {"$lte": now.replace(hour=23, minute=59) if hasattr(now, 'replace') else now},
            }
        ).to_list(20)

        payments = await database[C.PAYMENTS].find({"status": "paid"}).sort("createdAt", -1).limit(30).to_list(30)
        orders_by_day = await database[C.ORDERS].aggregate(
            [
                {"$group": {"_id": {"$dateToString": {"format": "%Y-%m-%d", "date": "$createdAt"}}, "count": {"$sum": 1}}},
                {"$sort": {"_id": -1}},
                {"$limit": 7},
            ]
        ).to_list(7)

        return {
            "totalCustomers": customers,
            "totalSellers": sellers,
            "totalProducts": products,
            "totalOrders": orders,
            "totalRevenue": round(revenue, 2),
            "activeSubscriptions": active_subs,
            "expiredSubscriptions": expired_subs,
            "pendingQuotaRequests": pending_quota,
            "topSellers": [
                {"sellerId": str(s["_id"]), "revenue": s["total"], "orders": s["count"]} for s in top_sellers
            ],
            "topProducts": [
                {"productId": str(p["_id"]), "title": p.get("title"), "sold": p["sold"]} for p in top_products
            ],
            "ordersChart": [{"date": d["_id"], "count": d["count"]} for d in orders_by_day],
            "recentPayments": serialize_docs(payments),
        }

    @staticmethod
    async def list_users(role: str | None = None) -> list:
        database = get_database()
        query = {}
        if role:
            query["role"] = role
        cursor = database[C.USERS].find(query).sort("createdAt", -1)
        from app.utils.helpers import serialize_docs

        return serialize_docs(await cursor.to_list(length=500))

    @staticmethod
    async def toggle_block(user_id: str, blocked: bool) -> None:
        database = get_database()
        await database[C.USERS].update_one(
            {"_id": oid(user_id)},
            {"$set": {"isBlocked": blocked, "updatedAt": utc_now()}},
        )
