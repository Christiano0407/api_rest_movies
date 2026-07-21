from datetime import datetime
from pydantic import BaseModel


class RequestTokenResponse(BaseModel):
    success: bool
    expires_at: datetime
    request_token: str


class SessionResponse(BaseModel):
    success: bool
    session_id: str


class TMDBAccountDetailsResponse(BaseModel):
    id: int
    username: str
