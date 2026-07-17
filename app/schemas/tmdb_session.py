from datetime import datetime
from pydantic import BaseModel, ConfigDict


class TMDBSessionCreate(BaseModel):
  tmdb_account_id: int | None = None
  tmdb_session_id: str


class TMDBSessionResponse(BaseModel):
  model_config = ConfigDict(from_attributes=True)
  id: int
  user_id: int
  tmdb_session_id: str
  tmdb_account_id:str
  connected_at: datetime