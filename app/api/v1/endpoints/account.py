"""
Flujo de ESCRITURA (Mutación / Sync). SQLAlchemy + Pydantic + HTTPX se dan la mano.
Pydantic (frontera) -> SQLAlchemy (extrae tmdb_session_id de Postgres) -> HTTPX (POST a TMDB).
"""

from fastapi import APIRouter, Depends, Query, Request, Response
from redis.asyncio import Redis
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_tmdb_client
from app.core.exceptions import BusinessLogicError
from app.db.session import get_db
from app.models.orm import TMDBSessions, Users
from app.schemas.tmdb_movies import WatchlistPayload
from app.services.tmdb_client import TMDBClient

router = APIRouter(prefix="/account", tags=["Account Users Sync & Roles & Access"])