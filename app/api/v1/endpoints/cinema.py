"""
Flujo de LECTURA (Cache-Aside + Proxy). No toca la RDB.
FastAPI -> Redis (rate limit) -> Redis (caché) -> [MISS] TMDB -> Pydantic (Adapter) -> Redis (SETEX).
"""

from collections.abc import Awaitable, Callable
from typing import Literal

from fastapi import APIRouter, Depends, Query, Response
from redis.asyncio import Redis

from app.api.deps import get_current_user, get_redis_dep
from app.core.config import settings
from app.models.orm import Users
from app.schemas.tmdb_movies import GatewayPaginationResponse, TMDBMovieResult
from app.services.rate_limiter import get_rate_limit_for_role, role_based_rate_limit
from app.services.tmdb_client import TMDBClient
#from app.services.cache import 

router = APIRouter(prefix="/cinema", tags=["Cinema Discovery"])

MovieCategory = Literal["now_playing", "popular", "top_rated", "upcoming"]