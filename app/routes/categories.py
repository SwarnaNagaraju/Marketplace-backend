from fastapi import APIRouter, Depends

from app.core.dependencies import require_roles
from app.database import get_database
from app.models import collections as C
from app.schemas.category import CategoryCreateRequest, CategoryUpdateRequest
from app.utils.helpers import oid, serialize_doc, serialize_docs, utc_now

router = APIRouter(prefix="/categories", tags=["Categories"])


@router.get("")
async def list_categories():
    database = get_database()
    cursor = database[C.CATEGORIES].find().sort("name", 1)
    return serialize_docs(await cursor.to_list(length=100))


@router.post("")
async def create_category(
    data: CategoryCreateRequest,
    _: dict = Depends(require_roles(["admin"])),
):
    database = get_database()
    doc = {**data.model_dump(), "createdAt": utc_now()}
    result = await database[C.CATEGORIES].insert_one(doc)
    doc["_id"] = result.inserted_id
    return serialize_doc(doc)


@router.put("/{category_id}")
async def update_category(
    category_id: str,
    data: CategoryUpdateRequest,
    _: dict = Depends(require_roles(["admin"])),
):
    database = get_database()
    updates = {k: v for k, v in data.model_dump(exclude_unset=True).items() if v is not None}
    await database[C.CATEGORIES].update_one({"_id": oid(category_id)}, {"$set": updates})
    cat = await database[C.CATEGORIES].find_one({"_id": oid(category_id)})
    return serialize_doc(cat)


@router.delete("/{category_id}")
async def delete_category(category_id: str, _: dict = Depends(require_roles(["admin"]))):
    database = get_database()
    await database[C.CATEGORIES].delete_one({"_id": oid(category_id)})
    return {"message": "Category deleted"}
