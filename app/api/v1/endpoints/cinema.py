"""
Flujo de LECTURA (Cache-Aside + Proxy). No toca la RDB.
FastAPI -> Redis (rate limit) -> Redis (caché) -> [MISS] TMDB -> Pydantic (Adapter) -> Redis (SETEX).
"""
from collections.abc import Awaitable, Callable
from typing import Literal

from fastapi import APIRouter, Depends, Query, Request, Response

from app.api.deps import get_cache_service, get_current_user, get_tmdb_client
from app.core.config import settings
from app.models.orm import Users
from app.schemas.tmdb_movies import GatewayPaginationResponse
from app.services.cache import CacheService
from app.services.rate_limiter import get_rate_limit_remaining
from app.services.tmdb_client import TMDBClient

router = APIRouter(prefix="/cinema", tags=["Cinema Discovery"])

MovieCategory = Literal["now_playing", "popular", "top_rated", "upcoming"]

# ---- Cache Key Helpers ---- #
def movies_list_cache_key(category: str, page: int) -> str:
  return f"cinema:movies:{category}:{page}"

def movies_search_cache_key(query: str, page: int) -> str:
  return f"cinema:movies:search:{query.lower()}:{page}"

# ---- Shared cache-aside core ---- #
async def _resolved_paginated_response(
    *,
    request: Request,
    response: Response,
    user: Users,
    cache: CacheService,
    cache_key: str,
    fetch_from_tmdb: Callable[[], Awaitable[GatewayPaginationResponse]],
) -> GatewayPaginationResponse:
  remaining = await get_rate_limit_remaining(request)
  limit = settings.RATE_LIMITS_PER_MINUTE.get(user.role, 60)
  response.headers["X-RateLimit-Limit"] = str(limit)
  response.headers["X-RateLimit-Remaining"] = str(remaining)

  data, from_cache = await cache.get_or_set(
    key=cache_key, factory=fetch_from_tmdb,
  )

  return GatewayPaginationResponse(
    **data.model_dump(exclude={"from_cache", "rate_limiting_remaining"}),
    from_cache=from_cache,
    rate_limiting_remaining=remaining,
  )

# ---- Search Movies ---- #
@router.get("/movies/search", response_model=GatewayPaginationResponse)
async def search_movies(
  *,
  request: Request,
  response: Response,
  query: str = Query(min_length=1, max_length=200, examples=["Star Wars"]),
  page: int = Query(default=1, ge=1, le=250),
  user: Users = Depends(get_current_user),
  cache: CacheService = Depends(get_cache_service),
  tmdb: TMDBClient = Depends(get_tmdb_client),
) -> GatewayPaginationResponse:
  return await _resolved_paginated_response(
    request=request, response=response, user=user, cache=cache,
    cache_key=movies_search_cache_key(query, page),
    fetch_from_tmdb=lambda: tmdb.search_movie(query, page),
  )

# ---- Movie Complementary Data ---- #
@router.get("/movies/{movie_id}/complementary")
async def get_movie_complementary(
  *,
  movie_id: int,
  user: Users = Depends(get_current_user),
  tmdb: TMDBClient = Depends(get_tmdb_client),
) -> dict:
  return await tmdb.get_complementary_data(movie_id)

# ---- Movies per Category ---- #
@router.get('/movies/{category}', response_model=GatewayPaginationResponse)
async def get_movies_category(
  *,
  request: Request,
  response: Response,
  category: MovieCategory,
  page: int = Query(default=1, ge=1, le=500),
  user: Users = Depends(get_current_user),
  cache: CacheService = Depends(get_cache_service),
  tmdb: TMDBClient = Depends(get_tmdb_client),
) -> GatewayPaginationResponse:
  return await _resolved_paginated_response(
    request=request, response=response, user=user, cache=cache,
    cache_key=movies_list_cache_key(category, page),
    fetch_from_tmdb=lambda: tmdb.get_movies_by_category(category, page),
  )
