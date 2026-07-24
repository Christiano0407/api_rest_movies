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

@router.post("/watchlist")
async def update_tmdb_watchlist(
  payload: WatchlistPayload,
  user: Users = Depends(get_current_user),
  db: AsyncSession = Depends(get_db), 
  tmdb: TMDBClient = Depends(get_tmdb_client)
) -> dict: 
  tmdb_sessions = await db.scalar(
    select(TMDBSessions).where(TMDBSessions.user_id == user.id)
  )
  if tmdb_sessions is None: 
    raise BusinessLogicError(
      "El usuario no ha vinculado una cuenta de TMDB en peste Gateway"
    )

  if tmdb_sessions.account_id is None: 
     raise BusinessLogicError("Cuenta de TMDB vinculada pero sin account_id. Re-vincula tu cuenta.")

  result = await tmdb.sync_watchlist(
    account_id=tmdb_sessions.account_id,
    session_id=tmdb_sessions.session_id,
    media_id=payload.media_id,
    media_type=payload.media_type,
    watchlist=payload.watchlist,
  )

  return {
    "success": result.success,
    "status_message": result.status_message,
  }