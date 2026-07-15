"""
    Service [auth]
"""

from __future__ import annotations

from datetime import UTC, datetime

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import AuthenticationError, ConflictError
from app.core.security import access_token, decode_token, hash_password, refresh_token, verify_password
from app.enums import RoleEnum
from app.models.orm import TokenBlocklist, Users
from app.schemas.auth import TokenResponse, UserRegister, UserResponse

logger = structlog.get_logger(__name__)


async def register_user(
    data: UserRegister,
    db: AsyncSession,
) -> UserResponse:
    existing = await db.execute(
        select(Users).where(
            (Users.username == data.username) | (Users.email == data.email)
        )
    )
    if existing.scalar_one_or_none():
        raise ConflictError("El usuario o email ya existe")

    user = Users(
        username=data.username,
        email=data.email,
        hashed_password=hash_password(data.password),
        role=RoleEnum.USER.value,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)

    logger.info("user_registered", user_id=user.id, username=user.username)
    return UserResponse.model_validate(user)


async def authenticate_user(
    username: str,
    password: str,
    db: AsyncSession,
) -> Users:
    result = await db.execute(select(Users).where(Users.username == username))
    user = result.scalar_one_or_none()

    if not user or not verify_password(password, user.hashed_password):
        raise AuthenticationError("Credenciales inválidas")

    if not user.is_active:
        raise AuthenticationError("Usuario desactivado")

    logger.info("user_authenticated", user_id=user.id, username=user.username)
    return user


async def create_tokens(user: Users) -> TokenResponse:
    access_jwt, _ = access_token(str(user.id), user.role)
    refresh_jwt, _ = refresh_token(str(user.id), user.role)

    return TokenResponse(
        access_token=access_jwt,
        refresh_token=refresh_jwt,
        token_type="bearer",
    )


async def refresh_access_token(
    refresh_token_str: str,
    db: AsyncSession,
) -> TokenResponse:
    payload = decode_token(refresh_token_str)

    if payload.get("type") != "refresh":
        raise AuthenticationError("Token inválido - se requiere refresh token")

    jti = payload.get("jti")
    result = await db.execute(
        select(TokenBlocklist).where(TokenBlocklist.jti == jti)
    )
    if result.scalar_one_or_none():
        raise AuthenticationError("Token ya fue revocado")

    user_id = payload.get("sub")
    result = await db.execute(select(Users).where(Users.id == int(user_id)))
    user = result.scalar_one_or_none()

    if not user or not user.is_active:
        raise AuthenticationError("Usuario no encontrado o desactivado")

    access_jwt, _ = access_token(str(user.id), user.role)
    refresh_jwt, _ = refresh_token(str(user.id), user.role)

    logger.info("token_refreshed", user_id=user.id)
    return TokenResponse(
        access_token=access_jwt,
        refresh_token=refresh_jwt,
        token_type="bearer",
    )


async def revoke_token(
    jti: str,
    token_type: str,
    user_id: int,
    expires_at: int | None,
    db: AsyncSession,
) -> None:
    entry = TokenBlocklist(
        jti=jti,
        token_type=token_type,
        user_id=user_id,
        expires_at=datetime.fromtimestamp(expires_at, tz=UTC) if expires_at else datetime.now(tz=UTC),
    )
    db.add(entry)
    await db.commit()
    logger.info("token_revoked", jti=jti, user_id=user_id)


async def logout_user(
    refresh_token_str: str,
    db: AsyncSession,
) -> None:
    payload = decode_token(refresh_token_str)

    if payload.get("type") != "refresh":
        raise AuthenticationError("Token inválido - se requiere refresh token")

    jti = payload.get("jti")
    user_id = int(payload.get("sub", 0))
    exp = payload.get("exp", 0)

    await revoke_token(jti, "refresh", user_id, exp, db)
    logger.info("user_logged_out", user_id=user_id)
