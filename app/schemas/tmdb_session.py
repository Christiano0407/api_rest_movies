from datetime import datetime
from pydantic import BaseModel, ConfigDict


class TMDBSessionCreate(BaseModel):
    session_id: str
    account_id: int | None = None


class TMDBLinkResponse(BaseModel): 
    session_id: str
    account_id: int | None = None


class TMDBAccountIdUpdate(BaseModel):
    account_id: int


class TMDBSessionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    user_id: int
    session_id: str
    account_id: int | None = None
    connected_at: datetime
