from app.core.exceptions import bad_request, forbidden, not_found
from app.database import get_database
from app.models import collections as C
from app.schemas.product import ProductCreateRequest, ProductUpdateRequest
from app.services.subscription_service import SubscriptionService
from app.utils.helpers import oid, serialize_doc, serialize_docs, utc_now
from app.utils.slug import slugify


class ProductService:
    @staticmethod
    async def list_products(
        q: str | None = None,
        category_id: str | None = None,
        seller_id: str | None = None,
        min_price: float | None = None,
        max_price: float | None = None,
        sort: str = "newest",
        skip: int = 0,
        limit: int = 20,
    ) -> list[dict]:
        database = get_database()
        query: dict = {"isDeleted": False, "isActive": True}
        if category_id:
            query["categoryId"] = oid(category_id)
        if seller_id:
            query["sellerId"] = oid(seller_id)
        if min_price is not None or max_price is not None:
            query["price"] = {}
            if min_price is not None:
                query["price"]["$gte"] = min_price
            if max_price is not None:
                query["price"]["$lte"] = max_price
        if q:
            query["$text"] = {"$search": q}

        sort_map = {
            "newest": [("createdAt", -1)],
            "price_asc": [("price", 1)],
            "price_desc": [("price", -1)],
            "rating": [("rating", -1)],
        }
        cursor = database[C.PRODUCTS].find(query).sort(sort_map.get(sort, [("createdAt", -1)])).skip(skip).limit(limit)
        products = await cursor.to_list(length=limit)
        return serialize_docs(products)

    @staticmethod
    async def get_by_slug(slug: str) -> dict:
        database = get_database()
        product = await database[C.PRODUCTS].find_one({"slug": slug, "isDeleted": False})
        if not product:
            raise not_found("Product not found")
        return serialize_doc(product)

    @staticmethod
    async def get_by_id(product_id: str) -> dict:
        database = get_database()
        product = await database[C.PRODUCTS].find_one({"_id": oid(product_id), "isDeleted": False})
        if not product:
            raise not_found("Product not found")
        return serialize_doc(product)

    @staticmethod
    async def create(seller: dict, data: ProductCreateRequest) -> dict:
        await SubscriptionService.validate_upload_eligibility(seller)
        database = get_database()
        category = await database[C.CATEGORIES].find_one({"_id": oid(data.categoryId)})
        if not category:
            raise bad_request("Invalid category")
        now = utc_now()
        effective_price = data.discountPrice if data.discountPrice else data.price
        doc = {
            "title": data.title,
            "slug": slugify(data.title),
            "description": data.description,
            "shortDescription": data.shortDescription or data.description[:120],
            "price": data.price,
            "discountPrice": data.discountPrice,
            "stock": data.stock,
            "brand": data.brand,
            "images": data.images,
            "thumbnail": data.thumbnail or (data.images[0] if data.images else None),
            "categoryId": oid(data.categoryId),
            "sellerId": oid(seller["id"]),
            "rating": 0,
            "totalReviews": 0,
            "specifications": data.specifications.model_dump() if data.specifications else {},
            "isActive": True,
            "isDeleted": False,
            "createdAt": now,
            "updatedAt": now,
        }
        try:
            result = await database[C.PRODUCTS].insert_one(doc)
            await SubscriptionService.consume_upload(seller["id"])
        except Exception:
            raise
        doc["_id"] = result.inserted_id
        return serialize_doc(doc)

    @staticmethod
    async def update(seller: dict, product_id: str, data: ProductUpdateRequest) -> dict:
        database = get_database()
        product = await database[C.PRODUCTS].find_one({"_id": oid(product_id), "isDeleted": False})
        if not product:
            raise not_found("Product not found")
        if str(product["sellerId"]) != seller["id"] and seller.get("role") != "admin":
            raise forbidden("Not your product")
        updates = {k: v for k, v in data.model_dump(exclude_unset=True).items() if v is not None}
        if "categoryId" in updates:
            updates["categoryId"] = oid(updates["categoryId"])
        if "specifications" in updates and updates["specifications"]:
            updates["specifications"] = data.specifications.model_dump()
        updates["updatedAt"] = utc_now()
        await database[C.PRODUCTS].update_one({"_id": oid(product_id)}, {"$set": updates})
        updated = await database[C.PRODUCTS].find_one({"_id": oid(product_id)})
        return serialize_doc(updated)

    @staticmethod
    async def delete(seller: dict, product_id: str) -> None:
        database = get_database()
        product = await database[C.PRODUCTS].find_one({"_id": oid(product_id)})
        if not product:
            raise not_found("Product not found")
        if str(product["sellerId"]) != seller["id"] and seller.get("role") != "admin":
            raise forbidden("Not your product")
        await database[C.PRODUCTS].update_one(
            {"_id": oid(product_id)},
            {"$set": {"isDeleted": True, "isActive": False, "updatedAt": utc_now()}},
        )

    @staticmethod
    async def seller_products(seller_id: str) -> list[dict]:
        database = get_database()
        cursor = database[C.PRODUCTS].find({"sellerId": oid(seller_id), "isDeleted": False}).sort("createdAt", -1)
        return serialize_docs(await cursor.to_list(length=500))
