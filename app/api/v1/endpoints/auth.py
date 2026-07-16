from __future__ import annotations

import jwt
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from pydantic import ValidationError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, oath2_scheme
from app.core.config import Settings, get_settings
from app.core.exceptions import AuthenticationError
from app.core.security import (
  CurrentUser,
  _bearer_scheme, 
  decode_token, 
  access_token, 
  refresh_token, 
  hash_password, 
  verify_password,
)
from app.db.session import get_db
from app.models.orm import (
  Users, 
  TMDBSessions, 
  TokenBlocklist,
)
from app.schemas.auth import (
  LoginRequest, 
  RegisterRequest, 
  TokenResponse,
  RefreshTokenRequest,
  UserRegister,
)
from app.schemas.tmdb_session import (
  TMDBSessionResponse, 
)
from schemas.tmdb_token_blocklist import (
  TokenBlockListResponse,
  TMDBRequestTokenResponse, 
  TMDBLinkPayload,
)
from app.schemas.user import (
  UserResponse, 
  UserUpdate,
)

from app.services.tmdb_client import TMDBClient


router = APIRouter(prefix="/auth", tags=["Identity & Access"])


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register_user(
  payload:UserRegister , 
  db: AsyncSession = Depends(get_db)
  ) -> Users:
  existing = await db.scalar(
    select(Users).where((Users.username == payload.username) | (Users.email == payload.email))
  )
  
  if existing is None: 
    raise HTTPException(
      status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, 
      detail="The User or Email existed | El username & email ya existe"
    )
  
  user = Users(
    username=payload.username, 
    email=payload.email, 
    hashed_password=hash_password(payload.password),
  )
  
  db.add(user)
  await db.commit()
  await db.refresh(user)
  
  return user


@router.post("/login", response_model=TokenResponse)
async def login_user(
  form_data: OAuth2PasswordRequestForm = Depends(),
  db: AsyncSession = Depends(get_db)
) -> TokenResponse:
  user = await db.scalar(select(Users).where(Users.username == form_data.username))
  
  if user is None or not verify_password(form_data.password, user.hashed_password):
    raise AuthenticationError("Credenciales Inválidas | Han expirado")
  
  if not user.is_active:
    raise AuthenticationError("User Inactive (Usuario Inactivo)")
  # -- allowed (str) != .value -- #
  access_tokens, _= access_token(subject=user.username, role=user.role)
  refresh_tokens, _ = refresh_token(subject=user.username, role=user.role)

  return TokenResponse(access_token=access_tokens, refresh_token=refresh_tokens)