from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.config.settings import get_settings
from app.database import close_db, connect_db
from app.routes import (
    admin,
    auth,
    cart,
    categories,
    notifications,
    orders,
    payments,
    products,
    quota,
    reviews,
    seller,
    subscriptions,
    uploads,
    users,
    wishlist,
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    await connect_db()
    from app.utils.seed import run_seed

    await run_seed()
    yield
    await close_db()


app = FastAPI(title="Multi-Vendor Marketplace API", version="1.0.0", lifespan=lifespan)

settings = get_settings()
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

base_dir = Path(__file__).resolve().parent.parent
upload_dir = base_dir / settings.upload_dir
upload_dir.mkdir(parents=True, exist_ok=True)
app.mount("/uploads", StaticFiles(directory=str(upload_dir)), name="uploads")

prefix = "/api/v1"

for router in [
    auth.router,
    users.router,
    categories.router,
    products.router,
    cart.router,
    orders.router,
    payments.router,
    subscriptions.router,
    quota.router,
    reviews.router,
    wishlist.router,
    admin.router,
    notifications.router,
    uploads.router,
    seller.router,
]:
    app.include_router(router, prefix=prefix)


@app.get("/health")
async def health():
    return {"status": "ok", "service": "marketplace-api"}
