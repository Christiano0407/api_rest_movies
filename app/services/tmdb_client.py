from __future__ import annotations

import asyncio
from typing import Any, Literal

import httpx
import structlog

from app.core.exceptions import BusinessLogicError, NotFoundError
from app.schemas.tmdb_auth import (
    RequestTokenResponse,
    SessionResponse,
    TMDBAccountDetailsResponse,
)
from app.schemas.tmdb_movies import GatewayPaginationResponse, WatchlistSyncResult

logger = structlog.get_logger(__name__)


class TMDBClient:
    def __init__(
        self,
        api_key: str | None = None,
        access_token: str | None = None,
        base_url: str = "https://api.themoviedb.org/3",
        timeout: int = 10,
        max_retries: int = 3,
    ) -> None:
        headers: dict[str, str] = {}
        params: dict[str, str] = {}

        if access_token:
            headers["Authorization"] = f"Bearer {access_token}"
        elif api_key:
            params["api_key"] = api_key

        self._client = httpx.AsyncClient(
            base_url=base_url,
            headers=headers,
            params=params,
            timeout=httpx.Timeout(timeout),
        )
        self.max_retries = max_retries

    async def _request(self, method: str, path: str, **kwargs: Any) -> dict[str, Any]:
        last_exc: Exception | None = None
        for attempt in range(self.max_retries):
            try:
                resp = await self._client.request(method, path, **kwargs)
            except httpx.RequestError as exc:
                logger.warning("tmdb_request_error", path=path, attempt=attempt, error=str(exc))
                last_exc = exc
                if attempt < self.max_retries - 1:
                    await asyncio.sleep(2**attempt)
                continue

            if resp.status_code == 429:
                raise BusinessLogicError(
                    f"TMDB rate limit. Retry-After: {resp.headers.get('Retry-After', '?')}s"
                )
            if resp.status_code == 404:
                raise NotFoundError("Resource not found in TMDB")
            if resp.is_error:
                logger.error("tmdb_api_error", path=path, status=resp.status_code, body=resp.text)
                raise BusinessLogicError(f"TMDB error {resp.status_code}: {resp.text[:200]}")

            return resp.json()

        raise BusinessLogicError(f"TMDB unavailable after {self.max_retries} attempts") from last_exc

    async def close(self) -> None:
        await self._client.aclose()

    # ── Auth Flow ──────────────────────────────────────────────────────

    async def create_request_token(self) -> RequestTokenResponse:
        data = await self._request("GET", "/authentication/token/new")
        return RequestTokenResponse(**data)

    async def create_session(self, request_token: str) -> SessionResponse:
        data = await self._request(
            "POST", "/authentication/session/new",
            json={"request_token": request_token},
        )
        return SessionResponse(**data)

    async def get_account_details(self, session_id: str) -> TMDBAccountDetailsResponse:
        data = await self._request("GET", "/account", params={"session_id": session_id})
        return TMDBAccountDetailsResponse(id=data["id"], username=data.get("username", ""))

    # ── Movies ─────────────────────────────────────────────────────────

    async def get_movies_by_category(
        self,
        category: Literal["now_playing", "popular", "top_rated", "upcoming"],
        page: int = 1,
    ) -> GatewayPaginationResponse:
        data = await self._request("GET", f"/movie/{category}", params={"page": page})
        return GatewayPaginationResponse(
            page=data.get("page", page),
            results=data.get("results", []),
            total_pages=data.get("total_pages", 0),
            total_results=data.get("total_results", 0),
        )

    async def get_movie_details(self, movie_id: int) -> dict[str, Any]:
        return await self._request("GET", f"/movie/{movie_id}")

    async def get_movie_credits(self, movie_id: int) -> dict[str, Any]:
        return await self._request("GET", f"/movie/{movie_id}/credits")

    async def get_movie_videos(self, movie_id: int) -> list[dict[str, Any]]:
        data = await self._request("GET", f"/movie/{movie_id}/videos")
        return data.get("results", [])

    async def get_complementary_data(self, movie_id: int) -> dict[str, Any]:
        details, credits, videos = await asyncio.gather(
            self.get_movie_details(movie_id),
            self.get_movie_credits(movie_id),
            self.get_movie_videos(movie_id),
        )
        return {"movie_id": movie_id, "details": details, "credits": credits, "videos": videos}

    # ── Watchlist ──────────────────────────────────────────────────────

    async def sync_watchlist(
        self,
        account_id: int,
        session_id: str,
        media_id: int,
        media_type: Literal["movie", "tv"],
        watchlist: bool,
    ) -> WatchlistSyncResult:
        data = await self._request(
            "POST",
            f"/account/{account_id}/watchlist",
            params={"session_id": session_id},
            json={"media_type": media_type, "media_id": media_id, "watchlist": watchlist},
        )
        return WatchlistSyncResult(
            success=data.get("success", False),
            status_message=data.get("status_message", ""),
        )

    # === ---- Search Movies ---- === #
    async def search_movie(self, query:str, page: int) -> GatewayPaginationResponse:
        data = await self._request("GET", "/search/movie", params={"query": query, "page": page})
        return GatewayPaginationResponse(
            page=data.get("page", page),
            results=data.get("results", []),
            total_pages=data.get("total_pages", 0),
            total_results=data.get("total_results", 0),
        )