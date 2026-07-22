"""
Service: Cache-Aside con Redis.
Patrón: GET Redis → [MISS] fetch from source → SETEX → return
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable

import structlog
from redis.asyncio import Redis

from app.schemas.tmdb_movies import GatewayPaginationResponse

logger = structlog.get_logger(__name__)


class CacheService:
  def __init__(self, redis: Redis, ttl: int = 120) -> None:
    self._redis = redis
    self._ttl = ttl # Define cuánto tiempo permanecerán los datos en Redis antes de expirar automáticamente.#

  async def _get_raw(self, key: str) -> str | None:
    try:
      return await self._redis.get(key)
    except Exception as exc:
      logger.warning('cache_get_error', key=key, error=str(exc))
      return None

  async def _set_raw(self, key: str, value: str, ttl: int | None = None) -> None:
    try:
      await self._redis.setex(key, ttl or self._ttl, value)
    except Exception as exc:
      logger.warning('cache_set_error', key=key, error=str(exc))

  async def delete(self, key: str) -> None:
    try:
      await self._redis.delete(key)
    except Exception as exc:
      logger.warning('cache_delete_error', key=key, error=str(exc))

  async def get_cached_movies(
    self, category: str, page: int,
  ) -> GatewayPaginationResponse | None:
    key = self.build_movie_key(category, page)
    raw = await self._get_raw(key)
    if raw is None:
      return None
    try:
      return GatewayPaginationResponse.model_validate_json(raw)
    except Exception as exc:
      logger.warning('cache_deserialize_error', key=key, error=str(exc))
      return None

  async def set_cached_movies(
    self, category: str, page: int, data: GatewayPaginationResponse,
    ttl: int | None = None,
  ) -> None:
    key = self.build_movie_key(category, page)
    await self._set_raw(key, data.model_dump_json(), ttl)

  async def get_cached_or_fetch(
    self,
    category: str,
    page: int,
    factory: Callable[[], Awaitable[GatewayPaginationResponse]],
    ttl: int | None = None,
  ) -> tuple[GatewayPaginationResponse, bool]:
    cached = await self.get_cached_movies(category, page)
    if cached is not None:
      return cached, True
    value = await factory()
    await self.set_cached_movies(category, page, value, ttl)
    return value, False

  @staticmethod
  def build_movie_key(category: str, page: int) -> str:
    return f'cinema:movies:{category}:{page}'
