from app.core.exceptions import bad_request
from app.database import get_database
from app.models import collections as C
from app.schemas.review import ReviewCreateRequest
from app.utils.helpers import oid, serialize_doc, serialize_docs, utc_now


class ReviewService:
    @staticmethod
    async def create(customer_id: str, data: ReviewCreateRequest) -> dict:
        database = get_database()
        product = await database[C.PRODUCTS].find_one({"_id": oid(data.productId)})
        if not product:
            raise bad_request("Product not found")
        existing = await database[C.REVIEWS].find_one(
            {"productId": oid(data.productId), "customerId": oid(customer_id)}
        )
        if existing:
            raise bad_request("You already reviewed this product")
        doc = {
            "productId": oid(data.productId),
            "customerId": oid(customer_id),
            "rating": data.rating,
            "reviewText": data.reviewText,
            "createdAt": utc_now(),
        }
        result = await database[C.REVIEWS].insert_one(doc)
        reviews = await database[C.REVIEWS].find({"productId": oid(data.productId)}).to_list(1000)
        avg = sum(r["rating"] for r in reviews) / len(reviews)
        await database[C.PRODUCTS].update_one(
            {"_id": oid(data.productId)},
            {"$set": {"rating": round(avg, 1), "totalReviews": len(reviews), "updatedAt": utc_now()}},
        )
        doc["_id"] = result.inserted_id
        updated_product = await database[C.PRODUCTS].find_one({"_id": oid(data.productId)})
        review_out = serialize_doc(doc)
        review_out["productRating"] = updated_product.get("rating", 0)
        review_out["productTotalReviews"] = updated_product.get("totalReviews", 0)
        return review_out

    @staticmethod
    async def by_product(product_id: str) -> list[dict]:
        database = get_database()
        cursor = database[C.REVIEWS].find({"productId": oid(product_id)}).sort("createdAt", -1)
        return serialize_docs(await cursor.to_list(length=100))
