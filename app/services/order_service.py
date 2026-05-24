import uuid
from collections import defaultdict

from app.core.exceptions import bad_request, forbidden, not_found
from app.database import get_database
from app.models import collections as C
from app.schemas.order import CheckoutRequest
from app.services.address_service import AddressService
from app.services.cart_service import CartService
from app.utils.helpers import oid, serialize_doc, serialize_docs, utc_now


class OrderService:
    @staticmethod
    def _generate_order_number() -> str:
        return f"ORD-{uuid.uuid4().hex[:10].upper()}"

    @staticmethod
    async def checkout(customer_id: str, data: CheckoutRequest) -> dict:
        cart = await CartService.get_or_create_cart(customer_id)
        if not cart.get("items"):
            raise bad_request("Cart is empty")

        shipping = await AddressService.resolve_checkout_address(
            customer_id,
            data.shippingAddress,
            data.useSavedAddress,
            data.saveAddress,
        )

        database = get_database()
        by_seller: dict[str, list] = defaultdict(list)
        for item in cart["items"]:
            product = await database[C.PRODUCTS].find_one({"_id": oid(item["productId"])})
            if not product or product["stock"] < item["quantity"]:
                raise bad_request(f"Product {item['productId']} unavailable")
            seller_id = str(product["sellerId"])
            price = product.get("discountPrice") or product["price"]
            by_seller[seller_id].append(
                {
                    "productId": oid(item["productId"]),
                    "title": product["title"],
                    "price": price,
                    "quantity": item["quantity"],
                    "subtotal": price * item["quantity"],
                }
            )

        now = utc_now()
        orders = []
        grand_total = 0
        for seller_id, products in by_seller.items():
            total_amount = sum(p["subtotal"] for p in products)
            tax_amount = round(total_amount * 0.05, 2)
            delivery_charge = 49.0 if total_amount < 500 else 0
            final_amount = total_amount + tax_amount + delivery_charge
            grand_total += final_amount
            order_doc = {
                "orderNumber": OrderService._generate_order_number(),
                "customerId": oid(customer_id),
                "sellerId": oid(seller_id),
                "products": products,
                "shippingAddress": shipping.model_dump(),
                "totalAmount": total_amount,
                "taxAmount": tax_amount,
                "deliveryCharge": delivery_charge,
                "finalAmount": final_amount,
                "paymentStatus": "pending",
                "orderStatus": "pending",
                "paymentId": None,
                "estimatedDeliveryDate": None,
                "deliveredAt": None,
                "createdAt": now,
                "updatedAt": now,
            }
            result = await database[C.ORDERS].insert_one(order_doc)
            order_doc["_id"] = result.inserted_id
            orders.append(serialize_doc(order_doc))

        await CartService.clear(customer_id)
        return {"orders": orders, "totalAmount": grand_total, "orderIds": [o["id"] for o in orders]}

    @staticmethod
    async def customer_orders(customer_id: str) -> list[dict]:
        database = get_database()
        cursor = database[C.ORDERS].find({"customerId": oid(customer_id)}).sort("createdAt", -1)
        return serialize_docs(await cursor.to_list(length=200))

    @staticmethod
    async def seller_orders(seller_id: str) -> list[dict]:
        database = get_database()
        cursor = database[C.ORDERS].find({"sellerId": oid(seller_id)}).sort("createdAt", -1)
        return serialize_docs(await cursor.to_list(length=200))

    @staticmethod
    async def update_status(user: dict, order_id: str, status: str) -> dict:
        database = get_database()
        order = await database[C.ORDERS].find_one({"_id": oid(order_id)})
        if not order:
            raise not_found("Order not found")
        role = user.get("role")
        if role == "seller" and str(order["sellerId"]) != user["id"]:
            raise forbidden("Not your order")
        if role not in ("seller", "admin"):
            raise forbidden()
        valid = ["confirmed", "processing", "shipped", "delivered", "cancelled", "rejected"]
        if status not in valid:
            raise bad_request(f"Invalid status. Use: {valid}")
        updates = {"orderStatus": status, "updatedAt": utc_now()}
        if status == "delivered":
            updates["deliveredAt"] = utc_now()
        await database[C.ORDERS].update_one({"_id": oid(order_id)}, {"$set": updates})
        updated = await database[C.ORDERS].find_one({"_id": oid(order_id)})
        return serialize_doc(updated)

    @staticmethod
    async def seller_action(seller_id: str, order_id: str, action: str) -> dict:
        if action not in ("confirm", "reject"):
            raise bad_request("action must be confirm or reject")
        status = "confirmed" if action == "confirm" else "rejected"
        database = get_database()
        order = await database[C.ORDERS].find_one({"_id": oid(order_id), "sellerId": oid(seller_id)})
        if not order:
            raise not_found("Order not found")
        if order.get("paymentStatus") != "paid":
            raise bad_request("Order not paid yet")
        await database[C.ORDERS].update_one(
            {"_id": oid(order_id)},
            {"$set": {"orderStatus": status, "updatedAt": utc_now()}},
        )
        return serialize_doc(await database[C.ORDERS].find_one({"_id": oid(order_id)}))
