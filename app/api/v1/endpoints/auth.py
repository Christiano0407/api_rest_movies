from __future__ import annotations

from datetime import UTC, datetime

import jwt
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from pydantic import ValidationError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import oath2_scheme, get_current_user
from app.core.exceptions import AuthenticationError
from app.core.security import access_token, decode_token, hash_password, refresh_token as create_refresh_token, verify_password
from app.db.session import get_db
from app.models.orm import TokenBlocklist, Users
from app.schemas.auth import RefreshTokenRequest, TokenResponse, UserRegister
from app.schemas.user import UserResponse
from app.schemas.tmdb_token_blocklist import ( 
  TMDBLinkPayload, TMDBRequestTokenResponse, 
  TokenBlockListCreate, TokenBlockListResponse)
from app.services.tmdb_client import TMDBClient
from app.services.auth import create_tokens


## === ---------- Router: AUTH [Endpoint] ----- ----- ##
router = APIRouter(prefix="/auth", tags=["Identity & Access"])

## === ---------- Register [Endpoint] ---------- ##
@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register_user(
    payload: UserRegister,
    db: AsyncSession = Depends(get_db),
) -> UserResponse:
    existing = await db.scalar(
        select(Users).where((Users.username == payload.username) | (Users.email == payload.email))
    )

    if existing is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="El username o email ya existe",
        )

    user = Users(
        username=payload.username,
        email=payload.email,
        hashed_password=hash_password(payload.password),
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)

    return UserResponse.model_validate(user)


## === ---------- login [Endpoint] ---------- ##
@router.post("/login", response_model=TokenResponse)
async def login_user(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: AsyncSession = Depends(get_db),
) -> TokenResponse:
    user = await db.scalar(select(Users).where(Users.username == form_data.username))

    if user is None or not verify_password(form_data.password, user.hashed_password):
        raise AuthenticationError("Credenciales Inválidas | Han expirado")

    if not user.is_active:
        raise AuthenticationError("User Inactive (Usuario Inactivo)")

    access_jwt, _ = access_token(subject=user.username, role=user.role)
    refresh_jwt, _ = create_refresh_token(subject=user.username, role=user.role)

    return TokenResponse(access_token=access_jwt, refresh_token=refresh_jwt)


## === ---------- Refresh [Endpoint] ---------- ##
@router.post("/refresh", response_model=TokenResponse)
async def refresh_access_token(
    payload: RefreshTokenRequest,
    db: AsyncSession = Depends(get_db),
) -> TokenResponse:
    """Rotación de Refresh Token: valida, revoca el usado (blocklist) y emite un par nuevo."""

    def _invalid() -> AuthenticationError:
        return AuthenticationError("Refresh Token Inválido o Revocado")

    try:
        decoded = decode_token(payload.refresh_token)
    except jwt.PyJWTError as exc:
        raise _invalid() from exc
    except ValidationError as exc:
        raise _invalid() from exc

    token_type: str = decoded.get("type", "")
    if token_type != "refresh":
        raise _invalid()

    jti: str = decoded.get("jti", "")
    already_used = await db.scalar(
        select(TokenBlocklist).where(TokenBlocklist.jti == jti)
    )
    if already_used is not None:
        raise _invalid()

    sub: str = decoded.get("sub", "")
    user = await db.scalar(select(Users).where(Users.username == sub))
    if user is None or not user.is_active:
        raise _invalid()

    exp: int = decoded.get("exp", 0)
    db.add(TokenBlocklist(
        jti=jti,
        token_type="refresh",
        subject=user.id,
        expires_at=datetime.fromtimestamp(exp, tz=UTC),
        revoked_at=datetime.now(tz=UTC),
    ))
    await db.commit()

    access_jwt, _ = access_token(subject=user.username, role=user.role)
    refresh_jwt, _ = create_refresh_token(subject=user.username, role=user.role)

    return TokenResponse(access_token=access_jwt, refresh_token=refresh_jwt)


## === ---------- Logout [Endpoint] ---------- ##
@router.post("/logout", status_code=status.HTTP_406_NOT_ACCEPTABLE)
async def logout(
    token: str = Depends(oath2_scheme), 
    user: Users = Depends(get_current_user), 
    db: AsyncSession = Depends(get_db)
) -> None:
    """Revoca el access token actual insertando su jti en el blocklist"""
    decoded = decode_token(token)
    jti: str = decoded.get("jti", "")
    exp: int = decoded.get("exp", 0)
    db.add(TokenBlocklist(
        jti=jti, 
        exp=datetime.fromtimestamp(exp, tz=UTC),
        ))
    await db.commit()
