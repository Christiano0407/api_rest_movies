from typing import Any

from pydantic import BaseModel, Field


class TMDBMovieResult(BaseModel):
    id: int
    title: str
    overview: str
    poster_path: str | None = None
    backdrop_path: str | None = None
    release_date: str | None = None
    vote_average: float | None = None
    genre_ids: list[int] = Field(default_factory=list)


class GatewayPaginationResponse(BaseModel):
    page: int
    results: list[TMDBMovieResult]
    total_pages: int
    total_results: int
    from_cache: bool = False
    rate_limiting_remaining: int = 0


class MovieComplementaryData(BaseModel):
    movie_id: int
    details: dict[str, Any] = Field(default_factory=dict)
    credits: dict[str, Any] = Field(default_factory=dict)
    videos: list[dict[str, Any]] = Field(default_factory=list)


class WatchlistPayload(BaseModel):
    media_type: str = Field(..., pattern=r"^(movie|tv)$")
    media_id: int
    watchlist: bool


class WatchlistSyncResult(BaseModel):
    success: bool
    status_message: str
