from app.config.settings import get_settings
from app.core.security import hash_password
from app.database import get_database
from app.models import collections as C
from app.utils.helpers import utc_now


async def run_seed() -> None:
    database = get_database()
    settings = get_settings()

    admin = await database[C.USERS].find_one({"email": settings.admin_seed_email.lower()})
    if not admin:
        await database[C.USERS].insert_one(
            {
                "name": "Platform Admin",
                "email": settings.admin_seed_email.lower(),
                "phone": "9999999999",
                "password": hash_password(settings.admin_seed_password),
                "role": "admin",
                "profileImage": None,
                "isBlocked": False,
                "isEmailVerified": True,
                "address": None,
                "walletBalance": 0,
                "createdAt": utc_now(),
                "updatedAt": utc_now(),
            }
        )

    plan_count = await database[C.SELLER_PLANS].count_documents({})
    if plan_count == 0:
        plans = [
            {
                "planName": "Basic",
                "weeklyFee": 99,
                "productUploadLimit": 10,
                "extraUploadPrice": 199,
                "features": ["10 uploads/week", "Basic support"],
                "isActive": True,
                "createdAt": utc_now(),
            },
            {
                "planName": "Standard",
                "weeklyFee": 299,
                "productUploadLimit": 50,
                "extraUploadPrice": 149,
                "features": ["50 uploads/week", "Priority listing"],
                "isActive": True,
                "createdAt": utc_now(),
            },
            {
                "planName": "Premium",
                "weeklyFee": 999,
                "productUploadLimit": 200,
                "extraUploadPrice": 99,
                "features": ["200 uploads/week", "Featured badge", "Analytics"],
                "isActive": True,
                "createdAt": utc_now(),
            },
        ]
        await database[C.SELLER_PLANS].insert_many(plans)

    cat_count = await database[C.CATEGORIES].count_documents({})
    if cat_count == 0:
        categories = [
            {"name": "Electronics", "description": "Gadgets and devices", "image": None, "createdAt": utc_now()},
            {"name": "Fashion", "description": "Clothing and accessories", "image": None, "createdAt": utc_now()},
            {"name": "Home", "description": "Home and kitchen", "image": None, "createdAt": utc_now()},
            {"name": "Books", "description": "Books and stationery", "image": None, "createdAt": utc_now()},
        ]
        await database[C.CATEGORIES].insert_many(categories)
