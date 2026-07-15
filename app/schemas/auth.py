from pydantic import BaseModel, EmailStr

class LoginRequest(BaseModel):
  email: EmailStr
  password: str


class RegisterRequest(BaseModel): 
  refresh_token: str


class TokenResponse(BaseModel):
  access_token: str
  token_type: str = "Bearer"


class TokenScheme(BaseModel):
  access_token: str
  refresh_token: str
  token_type: str = "Bearer"


class TokenPayload(BaseModel):
  sub: str
  role: str
  type: str
  jti: str


class RefreshTokenRequest(BaseModel):
  refresh_token: str