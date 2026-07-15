from datetime import datetime
from pydantic import BaseModel, ConfigDict, Field 
from enum import Enum


class TMDBMoviesResult(BaseModel):
  """Adapter: Valida & Normaliza el payload crudo por TMDB / Redis"""
  id: int = Field(examples=[11])
  title: str = Field(examples=["Star Wars"])
  overview: str
  poster_path: str | None = None
  backdrop_path: str | None = None
  release_date: str | None = None
  vote_average: float
  genre_ids: list[int] = Field(default_factory=list)


class GatewayPaginationResponse(BaseModel):
  """DTO Final del Gateway: TMDB + metadatos de Infraestructura inyectados"""
  page: int
  results: list[TMDBMoviesResult]
  total_pages: int
  total_results: int
  from_cache: bool
  rate_limit_remaining: int



# ======= ------- Watchlist ------ =======
class MediaType(str, Enum): 
  MOVIE = "movie"
  TV = "tv"


class WatchlistPayload(BaseModel):
  media_type: MediaType
  media_id: int
  watchlist: bool