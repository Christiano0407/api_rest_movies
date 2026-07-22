"""
Flujo de LECTURA (Cache-Aside + Proxy). No toca la RDB.
FastAPI -> Redis (rate limit) -> Redis (caché) -> [MISS] TMDB -> Pydantic (Adapter) -> Redis (SETEX).
"""
from collections.abc import Awaitable, Callable
from typing import Literal

from fastapi import APIRouter, Depends, Query, Request, Response
from redis.asyncio import Redis

from app.core.config import settings
from app.api.deps import get_cache_service, get_current_user, get_tmdb_client
from app.models.orm import Users
from app.schemas.tmdb_movies import GatewayPaginationResponse
from app.services.cache import CacheService
from app.services.rate_limiter import get_rate_limit_for_role, get_rate_limit_remaining, role_based_rate_limit
from app.services.tmdb_client import TMDBClient

router = APIRouter(prefix="/cinema", tags=["Cinema Discovery"])

MovieCategory = Literal["now_playing", "popular", "top_rated", "upcoming"]


# ------ Paginated Response ------ #
async def _resolved_paginated_response(
    *, 
    request: Request,
    response: Response, 
    user: Users, 
    redis:Redis, 
    category: str,
    page: int,  
    fetch_from_tmdb: Callable[[], Awaitable[GatewayPaginationResponse]],
) -> GatewayPaginationResponse:
  """
    Núcleo compartido del cache-aside — lo usan tanto el 
    listado por categoría como la búsqueda.
  """
  remaining = await get_rate_limit_remaining(request)
  limit = settings.RATE_LIMITS_PER_MINUTE.get(user.role, 60)
  response.headers["X-RateLimit-Limit"] = str(limit)
  response.headers["X-RateLimit-Remaining"] = str(remaining)

  cache_svc=CacheService(redis=redis, ttl=settings.CACHE_TTL_SECONDS)
  data, from_cache = await cache_svc.get_cached_or_fetch(
    category=category, page=page, factory=fetch_from_tmdb
  )

  return GatewayPaginationResponse(
    **data.model_dump(), 
    from_cache=from_cache, 
    rate_limiting_remaining = remaining,
  )


# ------ Search Movies ------ #


# ------ [Get] Movies per CATEGORY ------ #
""" 
@router.get('/movies/{category}', response_model=GatewayPaginationResponse)
@role_based_rate_limit('Users')
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
  ) """