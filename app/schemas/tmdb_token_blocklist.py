from datetime import datetime
from pydantic import BaseModel, ConfigDict


class TMDBRequestTokenResponse(BaseModel):
  request_token: str
  tmdb_authorize_url: str


class TMDBLinkPayload(BaseModel):
  request_token: str


class TokenBlockListCreate(BaseModel):
  jti: str
  expires_at: datetime


class TokenBlockListResponse(BaseModel):
  model_config = ConfigDict(from_attributes=True)
  id: int
  jti: str
  expires_at: datetime
  revoked_at: datetime
