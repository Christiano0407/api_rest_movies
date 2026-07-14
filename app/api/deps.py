"""
  - Este archivo unifica tus generadores de base de datos (get_db), la resolución 
    de la configuración global, tu cliente de caché y la instanciación limpia 
    de tu servicio de negocio.
    ------------------------------------------------------------------------------
    Dependencies transversales de FastAPI:
    - get_current_user: valida el JWT (firma RS256, expiración, blocklist).
    - require_roles: factory que arma un dependency de RBAC ("Admin", "Manager", ...).
"""  # noqa: E501

import jwt
from fastapi import Depends
from fastapi.security import OAuth2PasswordBearer
from pydantic import ValidationError
from redis.asyncio import Redis
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.config import settings
from app.core.exceptions import AuthenticationError, AuthorizationError
from app.core.security import decode_token
from app.core.redis_client import get_redis
from app.enums import RoleEnum
from app.db.session import get_db
from app.models.orm import Users, TMDBSessions, TokenBlocklist  

# redis_client |

# AUTH - Bearer
oath2_scheme = OAuth2PasswordBearer(tokenUrl=f"{settings.API_V1_PREFIX}/auth/login")

async def get_current_user(
    token: str = Depends(oath2_scheme), 
    db: AsyncSession = Depends(get_db)
) -> Users:
  try:
    payload = decode_token(token)
  except jwt.PyJWTError as exc:
    raise AuthenticationError("Token es Inválido o ha expirado") from exc
  except ValidationError as exc:
    raise AuthenticationError("Token, con estructura Inválida") from exc
  
  if payload.get("type") != "access":
    raise AuthenticationError("Se require un Access Token (No un Refresh Token)")
  
  blocked = await db.scalar(select(TokenBlocklist).where(
    TokenBlocklist.jti == payload.get("jti")
  ))
  if blocked is not None:
    raise AuthenticationError("Usuario Inválido")
 
  user = await db.scalar(select(Users).where(Users.user_name == payload.get("sub")))
  if user is None or not user.is_active:
    raise AuthenticationError("Usuario Inválido o Inactivo | Activa tu cuenta")
  
  return user
  



def require_roles(*roles: RoleEnum):
  pass 


async def get_redis_dep() -> Redis:
  pass