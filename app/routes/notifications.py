from fastapi import APIRouter, Depends

from app.core.dependencies import get_current_user
from app.database import get_database
from app.models import collections as C
from app.utils.helpers import oid, serialize_docs, utc_now

router = APIRouter(prefix="/notifications", tags=["Notifications"])


@router.get("")
async def list_notifications(user: dict = Depends(get_current_user)):
    database = get_database()
    cursor = database[C.NOTIFICATIONS].find({"userId": oid(user["id"])}).sort("createdAt", -1).limit(50)
    return serialize_docs(await cursor.to_list(length=50))


@router.patch("/{notification_id}/read")
async def mark_read(notification_id: str, user: dict = Depends(get_current_user)):
    database = get_database()
    await database[C.NOTIFICATIONS].update_one(
        {"_id": oid(notification_id), "userId": oid(user["id"])},
        {"$set": {"isRead": True}},
    )
    return {"message": "Marked as read"}


@router.patch("/read-all")
async def mark_all_read(user: dict = Depends(get_current_user)):
    database = get_database()
    await database[C.NOTIFICATIONS].update_many(
        {"userId": oid(user["id"])},
        {"$set": {"isRead": True}},
    )
    return {"message": "All marked as read"}
