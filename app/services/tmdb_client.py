from __future__ import annotations

from typing import Any, Literal

import httpx
import structlog
import asyncio
from aiocache import Cache

from app.core.exceptions import BusinessLogicError, NotFoundError
from app.schemas.tmdb_movies import ( 
    GatewayPaginationResponse, 
    WatchlistPayload, 
    WatchlistSyncResult 
    )
from app.schemas.tmdb_token_blocklist import TMDBRequestTokenResponse
from app.schemas.auth import (
    TokenResponse, 
    RefreshTokenRequest,
    UserRegister, 
    TMDBAccountResponse,
)
from app.schemas.tmdb_session import TMDBSessionResponse, TMDBAccountResponse

logger = structlog.get_logger(__name__)


class TMDBClient:
    def __init__(
            self, 
            api_key: str | None = None,
            access_toke: str | None = None, 
            base_url: str = "https://api.themoviedb.org/3", 
            redis: Cache, 
            timeout: int = 10, 
            max_retries: int = 3,
            ) -> None:
        header: dict[str, str] = {}
        params: dict[str, str] = {}

        if access_toke: 
            header["Authorization"] = f"Bearer {access_toke}"
        elif api_key: 
             params={"api_key": api_key}

        self._client = httpx.AsyncClient(
            base_url=base_url, 
            headers=header, 
            params=params, 
            timeout=httpx.Timeout(timeout)
            )
        self.cache = redis
        self.max_retries = max_retries

    async def _request(self, method:str, path: str, **kwargs: Any) -> dict[str, Any]:
        """Request & Rate Limiting"""
        last_exc: Exception | None = None
        for attempt in range(self.max_retries):
            try: 
                resp = await self._client.request(method, path, **kwargs)
            except httpx.RequestError as exc:
                logger.warning("tmdb_request_error", path=path, attempt=attempt, error=str(exc))
                last_exc = exc 
                if attempt < self.max_retries - 1: 
                    await asyncio.sleep(2 ** attempt)
                continue
            if resp.status_code == 429: 
                raise BusinessLogicError(f"TMDB rate limit. Retry-After: {resp.headers.get('retry-After', '?')}s")
            if resp.status_code == 404: 
                raise NotFoundError("Resource not found in TMDB")
            if resp.is_error:
                logger.error("tmdb_api_error", path=path, status=resp.status_code, body=resp.text)

            return resp.json()
        
        raise BusinessLogicError(f"TMDB unavailable after {self.max_retries}") from last_exc
    
    async def close(self) -> None:
        await self._client.aclose()

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
    # === ---- AUTH Flow ---- === #
    async def create_request_token(self) -> TokenResponse:
        """Obtener el Token desde TMDB"""
        data = await self._request("GET", "authentication/token/new")
        return TokenResponse(**data)
    
    async def create_session(self, request_token:str) -> TMDBSessionResponse:
        """Token - Session"""
        data = await self._request("POST", "/authentication/token/new", json={"request_token": request_token})
        return TMDBSessionResponse(**data)
    
    async def get_account_details(self, session_id:str) -> TMDBAccountResponse:
        """TMDB Details About Account"""
        data = await self._request("GET", "/account", params={"session_id": session_id})
        return TMDBAccountResponse(id=data["id"], username=data.get("username", ""))

    ## === ----- Movies ----- === ##

    ## === ----- WatchList ----- === ##