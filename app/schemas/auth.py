from typing import Literal, Optional

from pydantic import BaseModel, EmailStr, Field


class RegisterRequest(BaseModel):
    name: str = Field(min_length=2, max_length=100)
    email: EmailStr
    phone: str = Field(min_length=10, max_length=15)
    password: str = Field(min_length=6, max_length=128)
    role: Literal["customer", "seller"] = "customer"
    shopName: Optional[str] = None
    shopDescription: Optional[str] = None


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class SellerDetailsSchema(BaseModel):
    shopName: Optional[str] = None
    shopDescription: Optional[str] = None
    gstNumber: Optional[str] = None
    bankAccountNumber: Optional[str] = None
    ifscCode: Optional[str] = None
    upiId: Optional[str] = None


class UserUpdateRequest(BaseModel):
    name: Optional[str] = None
    phone: Optional[str] = None
    profileImage: Optional[str] = None
    address: Optional[dict] = None
    sellerDetails: Optional[SellerDetailsSchema] = None
