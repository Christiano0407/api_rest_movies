"""
Middleware ASGI de logging estructurado — corre para TODA petición, sin excepción.
(A diferencia del rate limiting, que es un `Depends()` por-endpoint porque necesita
saber el rol RBAC del usuario ya autenticado; ver app/services/rate_limiter.py.)
"""

import time 
import uuid

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from app.core.logging import get_logger

logger = get_logger(__name__)