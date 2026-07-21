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