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
from redis.asyncio import Redis
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.config import settings
from app.core.exceptions import AuthenticationError, AuthorizationError
from app.core.security import decode_token
from app.enums import RoleEnum
from app.db.session import get_db
from app.models.orm import Users, TMDBSessions, TokenBlocklist  

# redis_client |

# AUTH - Bearer
oath2_scheme = OAuth2PasswordBearer(tokenUrl=f"{settings.API_V1_PREFIX}/auth/login")