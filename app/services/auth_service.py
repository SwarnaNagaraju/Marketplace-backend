from app.core.exceptions import bad_request
from app.core.security import create_access_token, hash_password, verify_password
from app.database import get_database
from app.models import collections as C
from app.schemas.auth import LoginRequest, RegisterRequest
from app.utils.helpers import serialize_doc, utc_now


class AuthService:
    @staticmethod
    async def register(data: RegisterRequest) -> dict:
        database = get_database()
        existing = await database[C.USERS].find_one({"email": data.email.lower()})
        if existing:
            raise bad_request("Email already registered")
        user_doc = {
            "name": data.name,
            "email": data.email.lower(),
            "phone": data.phone,
            "password": hash_password(data.password),
            "role": data.role,
            "profileImage": None,
            "isBlocked": False,
            "isEmailVerified": False,
            "address": None,
            "walletBalance": 0,
            "createdAt": utc_now(),
            "updatedAt": utc_now(),
        }
        if data.role == "seller":
            user_doc["sellerDetails"] = {
                "shopName": data.shopName or f"{data.name}'s Shop",
                "shopDescription": data.shopDescription or "",
                "gstNumber": None,
                "bankAccountNumber": None,
                "ifscCode": None,
                "upiId": None,
            }
        result = await database[C.USERS].insert_one(user_doc)
        user_doc["_id"] = result.inserted_id
        user = serialize_doc(user_doc)
        token = create_access_token(user["id"], {"role": user["role"]})
        return {"access_token": token, "token_type": "bearer", "user": user}

    @staticmethod
    async def login(data: LoginRequest) -> dict:
        database = get_database()
        user = await database[C.USERS].find_one({"email": data.email.lower()})
        if not user or not verify_password(data.password, user["password"]):
            raise bad_request("Invalid email or password")
        if user.get("isBlocked"):
            raise bad_request("Account is blocked")
        user_serialized = serialize_doc(user)
        token = create_access_token(user_serialized["id"], {"role": user_serialized["role"]})
        return {"access_token": token, "token_type": "bearer", "user": user_serialized}
