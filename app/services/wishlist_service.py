from app.database import get_database
from app.models import collections as C
from app.utils.helpers import oid, serialize_doc, utc_now


class WishlistService:
    @staticmethod
    async def get(customer_id: str) -> dict:
        database = get_database()
        wl = await database[C.WISHLISTS].find_one({"customerId": oid(customer_id)})
        if wl:
            return serialize_doc(wl)
        now = utc_now()
        doc = {"customerId": oid(customer_id), "products": [], "createdAt": now}
        result = await database[C.WISHLISTS].insert_one(doc)
        doc["_id"] = result.inserted_id
        return serialize_doc(doc)

    @staticmethod
    async def toggle(customer_id: str, product_id: str) -> dict:
        database = get_database()
        wl = await WishlistService.get(customer_id)
        products = wl.get("products", [])
        if product_id in products:
            products = [p for p in products if p != product_id]
        else:
            products.append(product_id)
        await database[C.WISHLISTS].update_one(
            {"customerId": oid(customer_id)},
            {"$set": {"products": products}},
        )
        return await WishlistService.get(customer_id)
