from datetime import datetime

from pydantic import BaseModel, EmailStr, Field


class UserRegister(BaseModel):
    username: str = Field(..., min_length=3, max_length=30, examples=["alma_cantu"])
    email: EmailStr = Field(..., examples=["dev@example.com"])
    password: str = Field(..., min_length=8, examples=["developerStrongPassword01"])


class UserLogin(BaseModel):
    username: str = Field(..., examples=["alma_cantu"])
    password: str = Field(..., examples=["developerStrongPassword01"])


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class RefreshRequest(BaseModel):
    refresh_token: str


class UserResponse(BaseModel):
    id: int
    username: str
    email: str
    role: str
    is_active: bool
    created_at: datetime

    model_config = {"from_attributes": True}
