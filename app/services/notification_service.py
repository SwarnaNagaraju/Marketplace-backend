from app.database import get_database
from app.models import collections as C
from app.utils.helpers import oid, utc_now


async def create_notification(
    user_id: str,
    title: str,
    message: str,
    ntype: str = "admin",
) -> None:
    database = get_database()
    await database[C.NOTIFICATIONS].insert_one(
        {
            "userId": oid(user_id),
            "title": title,
            "message": message,
            "type": ntype,
            "isRead": False,
            "createdAt": utc_now(),
        }
    )
