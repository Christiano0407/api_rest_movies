"""
Flujo de LECTURA (Cache-Aside + Proxy). No toca la RDB.
FastAPI -> Redis (rate limit) -> Redis (caché) -> [MISS] TMDB -> Pydantic (Adapter) -> Redis (SETEX).
"""
from collections.abc import Awaitable, Callable
from typing import Literal

from fastapi import APIRouter, Depends, Query, Request, Response
from redis.asyncio import Redis

from app.core.config import settings
from app.api.deps import get_cache_service, get_current_user, get_tmdb_client, get_redis_dep
from app.models.orm import Users
from app.schemas.tmdb_movies import GatewayPaginationResponse
from app.services.cache import CacheService
from app.services.rate_limiter import get_rate_limit_for_role, get_rate_limit_remaining, role_based_rate_limit
from app.services.tmdb_client import TMDBClient

router = APIRouter(prefix="/cinema", tags=["Cinema Discovery"])

# === Movies Category === #
MovieCategory = Literal["now_playing", "popular", "top_rated", "upcoming"]

# ==== ----- Cache Key Helpers ---- ==== #
def movies_list_cache_key(category: str, page: int) -> str: 
  return f"Cinema:movies:{category}:{page}"

def movies_search_cache_key(query:str, page:int) -> str:
  return f"cinema:movies:search:{query.lower()}:{page}"

# ------ Paginated Response ------ #
async def _resolved_paginated_response(
    *, 
    request: Request,
    response: Response, 
    user: Users, 
    redis:Redis, 
    cache_key: str,
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

  try:
    raw = await redis.get(cache_key) 
  except Exception:
    raw = None

  if raw is not None: 
    try:
      data = GatewayPaginationResponse.model_validate_json(raw)
      return GatewayPaginationResponse(
        **data.model_dump(), 
        from_cache=True,
        rate_limiting_remaining=remaining,
      )
    except Exception: 
      pass

  data = await fetch_from_tmdb()

  try: 
    await redis.setex(cache_key, settings.CACHE_TTL_SECONDS, data.model_dump_json())
  except Exception:
    pass

  return GatewayPaginationResponse(
    **data.model_dump(), # model_dump() (Pydantic v2) convierte el modelo en un diccionario.
    from_cache=False, 
    rate_limiting_remaining = remaining,
  )


# ------ Search Movies ------ #
@router.get("/movies/search", response_model=GatewayPaginationResponse)
async def search_movies(
  *,
  request: Request, 
  response: Response, 
  query: str = Query(min_length=1, max_length=200, examples=["Star Wars"]), 
  page: int = Query(default=1, ge=1, le=250), 
  user: Users = Depends(get_current_user), 
  redis: Redis = Depends(get_redis_dep), 
  tmdb: TMDBClient = Depends(get_tmdb_client),
) -> GatewayPaginationResponse:
  return await _resolved_paginated_response(
    request=request, 
    response=response, 
    user=user, 
    redis=redis,
    cache_key=movies_search_cache_key(query, page), 
    fetch_from_tmdb=lambda: tmdb.search_movie(query, page), 
  )

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