from app.core.exceptions import bad_request, not_found
from app.database import get_database
from app.models import collections as C
from app.utils.helpers import oid, serialize_doc, utc_now


class CartService:
    @staticmethod
    async def get_or_create_cart(customer_id: str) -> dict:
        database = get_database()
        cart = await database[C.CARTS].find_one({"customerId": oid(customer_id)})
        if cart:
            return serialize_doc(cart)
        now = utc_now()
        doc = {"customerId": oid(customer_id), "items": [], "totalAmount": 0, "createdAt": now, "updatedAt": now}
        result = await database[C.CARTS].insert_one(doc)
        doc["_id"] = result.inserted_id
        return serialize_doc(doc)

    @staticmethod
    async def _recalculate(cart_id) -> None:
        database = get_database()
        cart = await database[C.CARTS].find_one({"_id": cart_id})
        total = sum(item["subtotal"] for item in cart.get("items", []))
        await database[C.CARTS].update_one(
            {"_id": cart_id},
            {"$set": {"totalAmount": total, "updatedAt": utc_now()}},
        )

    @staticmethod
    async def add_item(customer_id: str, product_id: str, quantity: int) -> dict:
        database = get_database()
        product = await database[C.PRODUCTS].find_one(
            {"_id": oid(product_id), "isActive": True, "isDeleted": False}
        )
        if not product:
            raise not_found("Product not found")
        if product["stock"] < quantity:
            raise bad_request("Insufficient stock")
        cart = await CartService.get_or_create_cart(customer_id)
        price = product.get("discountPrice") or product["price"]
        items = cart.get("items", [])
        found = False
        for item in items:
            if item["productId"] == product_id:
                item["quantity"] += quantity
                item["subtotal"] = item["quantity"] * item["price"]
                found = True
                break
        if not found:
            items.append(
                {
                    "productId": product_id,
                    "sellerId": str(product["sellerId"]),
                    "quantity": quantity,
                    "price": price,
                    "subtotal": price * quantity,
                }
            )
        await database[C.CARTS].update_one(
            {"_id": oid(cart["id"])},
            {"$set": {"items": items, "updatedAt": utc_now()}},
        )
        await CartService._recalculate(oid(cart["id"]))
        return await CartService.get_or_create_cart(customer_id)

    @staticmethod
    async def update_quantity(customer_id: str, product_id: str, quantity: int) -> dict:
        database = get_database()
        cart = await database[C.CARTS].find_one({"customerId": oid(customer_id)})
        if not cart:
            raise not_found("Cart not found")
        items = cart.get("items", [])
        new_items = []
        for item in items:
            if str(item["productId"]) == product_id:
                product = await database[C.PRODUCTS].find_one({"_id": oid(product_id)})
                price = product.get("discountPrice") or product["price"]
                item["quantity"] = quantity
                item["price"] = price
                item["subtotal"] = price * quantity
            new_items.append(item)
        await database[C.CARTS].update_one(
            {"_id": cart["_id"]},
            {"$set": {"items": new_items, "updatedAt": utc_now()}},
        )
        await CartService._recalculate(cart["_id"])
        return await CartService.get_or_create_cart(customer_id)

    @staticmethod
    async def remove_item(customer_id: str, product_id: str) -> dict:
        database = get_database()
        cart = await database[C.CARTS].find_one({"customerId": oid(customer_id)})
        if not cart:
            raise not_found("Cart not found")
        items = [i for i in cart.get("items", []) if str(i["productId"]) != product_id]
        await database[C.CARTS].update_one(
            {"_id": cart["_id"]},
            {"$set": {"items": items, "updatedAt": utc_now()}},
        )
        await CartService._recalculate(cart["_id"])
        return await CartService.get_or_create_cart(customer_id)

    @staticmethod
    async def clear(customer_id: str) -> dict:
        database = get_database()
        await database[C.CARTS].update_one(
            {"customerId": oid(customer_id)},
            {"$set": {"items": [], "totalAmount": 0, "updatedAt": utc_now()}},
        )
        return await CartService.get_or_create_cart(customer_id)
