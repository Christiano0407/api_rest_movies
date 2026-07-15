from __future__ import annotations

from typing import Any, Literal

import httpx
import structlog
from aiocache import Cache

from app.core.exceptions import BusinessLogicError, NotFoundError
from app.schemas.tmdb_movies import GatewayPaginationResponse

logger = structlog.get_logger(__name__)


class TMDBClient:
    def __init__(self, api_key: str, base_url: str, redis: Cache):
        self._client = httpx.AsyncClient(base_url=base_url, params={"api_key": api_key})
        self.cache = redis

    async def get_movies_by_category(
        self,
        category: Literal["now_playing", "popular", "top_rated", "upcoming"],
        page: int = 1,
    ) -> GatewayPaginationResponse:
        path = f"/movie/{category}"
        params: dict[str, Any] = {"page": page}
        try:
            resp = await self._client.get(path, params=params)
            resp.raise_for_status()
        except httpx.HTTPStatusError as exc:
            logger.error("tmdb_api_error", path=path, status=exc.response.status_code)
            if exc.response.status_code == 404:
                raise NotFoundError("Categoría no encontrada en TMDB")
            raise BusinessLogicError(f"Error al consultar TMDB: {exc.response.status_code}")
        except httpx.RequestError as exc:
            logger.error("tmdb_connection_error", path=path, error=str(exc))
            raise BusinessLogicError("No se pudo conectar con TMDB")

        data = resp.json()
        return GatewayPaginationResponse(
            page=data.get("page", page),
            results=data.get("results", []),
            total_pages=data.get("total_pages", 0),
            total_results=data.get("total_results", 0),
            from_cache=False,
            rate_limiting_remaining=0,
        )

    async def close(self) -> None:
        await self._client.aclose()
