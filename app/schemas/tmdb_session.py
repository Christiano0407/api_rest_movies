from datetime import datetime
from pydantic import BaseModel, ConfigDict


class TMDBSessionCreate(BaseModel):
  tmdb_account_id: int
  tmdb_session_id: str


class TMDBSessionResponse(BaseModel):
  model_config = ConfigDict(from_attributes=True)
  id: int
  user__id: int
  tmdb_account_id:str
  connected_at: datetime