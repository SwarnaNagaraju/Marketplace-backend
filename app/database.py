from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase

from app.config.settings import get_settings
from app.models import collections as C

client: AsyncIOMotorClient | None = None
db: AsyncIOMotorDatabase | None = None


async def connect_db() -> None:
    global client, db
    settings = get_settings()
    client = AsyncIOMotorClient(settings.mongodb_uri)
    db = client[settings.database_name]
    await create_indexes()


async def close_db() -> None:
    global client
    if client:
        client.close()


def get_database() -> AsyncIOMotorDatabase:
    if db is None:
        raise RuntimeError("Database not initialized")
    return db


async def create_indexes() -> None:
    database = get_database()
    await database[C.USERS].create_index("email", unique=True)
    await database[C.PRODUCTS].create_index("categoryId")
    await database[C.PRODUCTS].create_index("sellerId")
    await database[C.PRODUCTS].create_index("slug", unique=True, sparse=True)
    await database[C.PRODUCTS].create_index([("title", "text"), ("description", "text")])
    await database[C.ORDERS].create_index("customerId")
    await database[C.ORDERS].create_index("sellerId")
    await database[C.ORDERS].create_index("orderNumber", unique=True)
    await database[C.PAYMENTS].create_index("userId")
    await database[C.PAYMENTS].create_index("razorpayOrderId")
    await database[C.SELLER_SUBSCRIPTIONS].create_index([("sellerId", 1), ("status", 1)])
    await database[C.QUOTA_REQUESTS].create_index([("sellerId", 1), ("adminApprovalStatus", 1)])
    await database[C.CARTS].create_index("customerId", unique=True)
    await database[C.WISHLISTS].create_index("customerId", unique=True)
