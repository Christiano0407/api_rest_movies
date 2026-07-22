"""
  === TMDB | Vinculación de cuenta real de TMDB (requerido por /account/watchlist) ===
"""

from __future__ import annotations

from datetime import UTC, datetime
import jwt
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from pydantic import ValidationError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, oath2_scheme, get_tmdb_client
from app.core.exceptions import AuthenticationError
from app.core.security import (
  access_token, 
  decode_token, 
  hash_password, 
  refresh_token as create_refresh_token,
   verify_password
)
from app.db.session import get_db
from app.models.orm import (
  TokenBlocklist, 
  Users, 
  TMDBSessions,
)
from app.schemas.tmdb_session import TMDBLinkResponse, TMDBSessionResponse
from app.schemas.tmdb_auth import (
  RequestTokenResponse, 
  SessionResponse, 
  TMDBAccountDetailsResponse, 
)
from app.schemas.user import UserResponse, UserRegister
from app.schemas.tmdb_token_blocklist import ( 
  TMDBLinkPayload, TMDBRequestTokenResponse, 
  TokenBlockListCreate, TokenBlockListResponse
)
from app.services.tmdb_client import TMDBClient

router = APIRouter(prefix="/auth", tags=["Identity & Access"])

## === ---------- Vinculación de cuenta TMDB  ---------- ##
@router.post("/tmdb/request-token", response_model=TMDBRequestTokenResponse)
async def create_tmdb_request_token(
  tmdb: TMDBClient = Depends(get_tmdb_client), 
  user: Users = Depends(get_current_user)) -> TMDBRequestTokenResponse: 
  request_token_data = await tmdb.create_request_token()
  authorization_url = f"https://www.themoviedb.org/authenticate/{request_token_data}"
  return TMDBRequestTokenResponse(
    request_token=request_token_data.request_token, 
    tmdb_authorize_url=authorization_url
    )


@router.post("/tmdb/link", response_model=TMDBSessionResponse, status_code=201)
async def link_tmdb_account(
  payload: TMDBLinkPayload, 
  user: Users = Depends(get_current_user),
  db: AsyncSession = Depends(get_db),
  tmdb: TMDBClient = Depends(get_tmdb_client),
) -> TMDBSessionResponse: 
  """
    Canjea el request_token aprobado por un session_id real y 
    lo persiste (upsert) en tmdb_sessions.
  """
  session_data = await tmdb.create_session(payload.request_token)
  account_data = await tmdb.get_account_details(session_data.session_id)

  existing = await db.scalar(
    select(TMDBSessions).where(TMDBSessions.user_id == user.id)
  )
  if existing is not None: 
    existing.session_id = session_data.session_id
    existing.account_id = account_data.id
  else: 
    existing = TMDBSessions(
      user_id=user.id, 
      session_id=session_data.session_id, 
      account_id=account_data.id
      )
    db.add(existing)

  await db.commit()
  await db.refresh(existing)
  return TMDBSessionResponse.model_validate(existing)