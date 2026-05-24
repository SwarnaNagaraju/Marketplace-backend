from typing import Callable

from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.core.exceptions import forbidden, unauthorized
from app.core.security import decode_access_token
from app.database import get_database
from app.models import collections as C
from app.utils.helpers import oid, serialize_doc

security = HTTPBearer(auto_error=False)


async def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(security),
) -> dict:
    if not credentials:
        raise unauthorized()
    try:
        payload = decode_access_token(credentials.credentials)
    except ValueError:
        raise unauthorized("Invalid or expired token")
    user_id = payload.get("sub")
    if not user_id:
        raise unauthorized()
    database = get_database()
    user = await database[C.USERS].find_one({"_id": oid(user_id)})
    if not user:
        raise unauthorized("User not found")
    if user.get("isBlocked"):
        raise forbidden("Account is blocked")
    return serialize_doc(user)


def require_roles(allowed: list[str]) -> Callable:
    async def role_checker(user: dict = Depends(get_current_user)) -> dict:
        if user.get("role") not in allowed:
            raise forbidden(f"Requires one of roles: {', '.join(allowed)}")
        return user

    return role_checker
