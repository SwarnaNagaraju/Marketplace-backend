from pydantic import BaseModel, ConfigDict


class PyObjectIdMixin(BaseModel):
    model_config = ConfigDict(populate_by_name=True, from_attributes=True)


class MessageResponse(BaseModel):
    message: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: dict
