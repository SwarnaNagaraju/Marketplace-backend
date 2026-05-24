from datetime import datetime, timezone
from typing import Any

from bson import ObjectId


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def oid(value: str | ObjectId) -> ObjectId:
    if isinstance(value, ObjectId):
        return value
    return ObjectId(value)


def serialize_doc(doc: dict[str, Any] | None) -> dict[str, Any] | None:
    if not doc:
        return None
    out = dict(doc)
    if "_id" in out:
        out["id"] = str(out.pop("_id"))
    for key, val in list(out.items()):
        if isinstance(val, ObjectId):
            out[key] = str(val)
        elif isinstance(val, datetime):
            out[key] = val.isoformat()
        elif isinstance(val, list):
            out[key] = [
                serialize_doc(v) if isinstance(v, dict) else str(v) if isinstance(v, ObjectId) else v
                for v in val
            ]
        elif isinstance(val, dict):
            out[key] = serialize_doc(val)
    if "password" in out:
        del out["password"]
    return out


def serialize_docs(docs: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [serialize_doc(d) for d in docs if d]
