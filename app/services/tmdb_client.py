from __future__ import annotations

from app.core.config import Settings, get_settings
from app.models.orm import (
  TMDBSessions,
  TokenBlocklist,
)
from app.schemas.tmdb_movies import (
  GatewayPaginationResponse,
)


class TMDBClient: 
  def __init__(
      self, 
      api_key: str, 
      base_url: str,  
  ) -> GatewayPaginationResponse:
  pass