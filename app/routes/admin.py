from fastapi import APIRouter, Depends, Query

from app.core.dependencies import require_roles
from app.database import get_database
from app.models import collections as C
from app.schemas.quota import QuotaAdminAction
from app.schemas.subscription import PlanCreateRequest, PlanUpdateRequest
from app.services.admin_service import AdminService
from app.services.quota_service import QuotaService
from app.utils.helpers import oid, serialize_doc, serialize_docs, utc_now

router = APIRouter(prefix="/admin", tags=["Admin"])


@router.get("/dashboard")
async def dashboard(_: dict = Depends(require_roles(["admin"]))):
    return await AdminService.dashboard_stats()


@router.get("/users")
async def list_users(role: str | None = None, _: dict = Depends(require_roles(["admin"]))):
    return await AdminService.list_users(role)


@router.patch("/users/{user_id}/block")
async def block_user(
    user_id: str,
    blocked: bool = Query(True),
    _: dict = Depends(require_roles(["admin"])),
):
    await AdminService.toggle_block(user_id, blocked)
    return {"message": "User updated"}


@router.get("/quota-requests")
async def pending_quota(_: dict = Depends(require_roles(["admin"]))):
    return await QuotaService.pending_requests()


@router.patch("/quota-requests/{request_id}")
async def quota_action(
    request_id: str,
    data: QuotaAdminAction,
    user: dict = Depends(require_roles(["admin"])),
):
    return await QuotaService.admin_action(user, request_id, data.action, data.adminMessage)


@router.get("/plans")
async def admin_plans(_: dict = Depends(require_roles(["admin"]))):
    database = get_database()
    return serialize_docs(await database[C.SELLER_PLANS].find().to_list(50))


@router.post("/plans")
async def create_plan(data: PlanCreateRequest, _: dict = Depends(require_roles(["admin"]))):
    database = get_database()
    doc = {**data.model_dump(), "createdAt": utc_now()}
    result = await database[C.SELLER_PLANS].insert_one(doc)
    doc["_id"] = result.inserted_id
    return serialize_doc(doc)


@router.put("/plans/{plan_id}")
async def update_plan(
    plan_id: str,
    data: PlanUpdateRequest,
    _: dict = Depends(require_roles(["admin"])),
):
    database = get_database()
    updates = {k: v for k, v in data.model_dump(exclude_unset=True).items() if v is not None}
    await database[C.SELLER_PLANS].update_one({"_id": oid(plan_id)}, {"$set": updates})
    plan = await database[C.SELLER_PLANS].find_one({"_id": oid(plan_id)})
    return serialize_doc(plan)


@router.get("/orders")
async def all_orders(_: dict = Depends(require_roles(["admin"]))):
    database = get_database()
    cursor = database[C.ORDERS].find().sort("createdAt", -1)
    return serialize_docs(await cursor.to_list(length=500))


@router.get("/products")
async def all_products(_: dict = Depends(require_roles(["admin"]))):
    database = get_database()
    cursor = database[C.PRODUCTS].find({"isDeleted": False}).sort("createdAt", -1)
    return serialize_docs(await cursor.to_list(length=500))
