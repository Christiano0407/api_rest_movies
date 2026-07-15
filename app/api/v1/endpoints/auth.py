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
  UserResponse, 
  UserUpdate,
)

