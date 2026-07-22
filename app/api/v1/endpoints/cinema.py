"""
Flujo de LECTURA (Cache-Aside + Proxy). No toca la RDB.
FastAPI -> Redis (rate limit) -> Redis (caché) -> [MISS] TMDB -> Pydantic (Adapter) -> Redis (SETEX).
"""

from typing import Literal

from fastapi import APIRouter, Depends, Query, Request

from app.api.deps import get_cache_service, get_current_user, get_tmdb_client
from app.models.orm import Users
from app.schemas.tmdb_movies import GatewayPaginationResponse
from app.services.cache import CacheService
from app.services.rate_limiter import get_rate_limit_remaining, role_based_rate_limit
from app.services.tmdb_client import TMDBClient

router = APIRouter(prefix="/cinema", tags=["Cinema Discovery"])

MovieCategory = Literal["now_playing", "popular", "top_rated", "upcoming"]


@router.get('/movies/{category}', response_model=GatewayPaginationResponse)
@role_based_rate_limit('User')
async def get_movies_by_category(
  category: MovieCategory,
  page: int = Query(1, ge=1, le=500),
  request: Request,
  current_user: Users = Depends(get_current_user),
  cache: CacheService = Depends(get_cache_service),
  tmdb: TMDBClient = Depends(get_tmdb_client),
) -> GatewayPaginationResponse:
  data, from_cache = await cache.get_cached_or_fetch(
    category=category,
    page=page,
    factory=lambda: tmdb.get_movies_by_category(category, page),
  )
  remaining = get_rate_limit_remaining(request)
  return GatewayPaginationResponse(
    **data.model_dump(),
    from_cache=from_cache,
    rate_limiting_remaining=remaining,
  )