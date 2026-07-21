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

from app.api.deps import get_current_user, oath2_scheme
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
from app.schemas.tmdb_session import TMDBLinkResponse
from app.schemas.tmdb_auth import (
  RequestTokenResponse, 
  SessionResponse, 
  TMDBAccountDetailsResponse
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
async def create_tmdb_request_token(self, 
  user: Users = Depends(get_current_user)) -> TMDBRequestTokenResponse: 
  request_token = await self.TMDBClient.create_request_token()
  authorization_url = f"https://www.themoviedb.org/authenticate/{request_token}"
  return TMDBRequestTokenResponse(
    request_token=request_token, tmdb_authorize_url=authorization_url)

""" 
@router.post("/tmdb/link", response_model=TMDBLinkResponse)
async def link_tmdb_account(self,
  payload: TMDBLinkPayload, 
  user: Users = Depends(get_current_user),
  db: AsyncSession = Depends(get_db),
) -> TMDBLinkResponse: 
  """
    Canjea el request_token aprobado por un session_id real y 
    lo persiste (upsert) en tmdb_sessions.
  """
  session_id = await self.TMDBClient.create_session(payload.request_token)
  account = await self.TMDBClient.get_account_details(session_id)

  existing = await db.scalar(
    select(TMDBSessions).where(TMDBSessions.user_id == user.id)
  )
  if existing is not None: 
    existing.session_id = session_id
    existing.account_id = account
  else: 
    db.add(TMDBSessions(user_id=user.id), tmdb_account_id=str(account["id"]), tmdb_session_id=session_id)
    await db.commit()
    return TMDBLinkResponse() """