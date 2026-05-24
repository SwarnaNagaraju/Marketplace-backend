from fastapi import APIRouter, Depends

from app.core.dependencies import get_current_user
from app.schemas.auth import LoginRequest, RegisterRequest
from app.schemas.common import TokenResponse
from app.services.auth_service import AuthService

router = APIRouter(prefix="/auth", tags=["Auth"])


@router.post("/register", response_model=TokenResponse)
async def register(data: RegisterRequest):
    return await AuthService.register(data)


@router.post("/login", response_model=TokenResponse)
async def login(data: LoginRequest):
    return await AuthService.login(data)


@router.get("/me")
async def me(user: dict = Depends(get_current_user)):
    return user
