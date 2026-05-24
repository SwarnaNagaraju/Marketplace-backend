from fastapi import APIRouter, Depends, Query

from app.core.dependencies import get_current_user, require_roles
from app.schemas.product import ProductCreateRequest, ProductUpdateRequest
from app.services.product_service import ProductService

router = APIRouter(prefix="/products", tags=["Products"])


@router.get("")
async def list_products(
    q: str | None = None,
    categoryId: str | None = None,
    sellerId: str | None = None,
    minPrice: float | None = None,
    maxPrice: float | None = None,
    sort: str = "newest",
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
):
    return await ProductService.list_products(q, categoryId, sellerId, minPrice, maxPrice, sort, skip, limit)


@router.get("/slug/{slug}")
async def get_by_slug(slug: str):
    return await ProductService.get_by_slug(slug)


@router.get("/seller/mine")
async def my_products(user: dict = Depends(require_roles(["seller"]))):
    return await ProductService.seller_products(user["id"])


@router.get("/{product_id}")
async def get_product(product_id: str):
    return await ProductService.get_by_id(product_id)


@router.post("")
async def create_product(
    data: ProductCreateRequest,
    user: dict = Depends(require_roles(["seller"])),
):
    return await ProductService.create(user, data)


@router.put("/{product_id}")
async def update_product(
    product_id: str,
    data: ProductUpdateRequest,
    user: dict = Depends(require_roles(["seller", "admin"])),
):
    return await ProductService.update(user, product_id, data)


@router.delete("/{product_id}")
async def delete_product(
    product_id: str,
    user: dict = Depends(require_roles(["seller", "admin"])),
):
    await ProductService.delete(user, product_id)
    return {"message": "Product deleted"}
