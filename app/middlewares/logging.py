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


class RequestLoggingMiddlewares(BaseHTTPMiddleware): 
  async def dispatch(self, request:Request, call_next) -> Response:
    request_id = request.headers.get("X-Request-ID", str(uuid.uuid4))
    start = time.perf_counter()

    response = await call_next(request)

    duration_ms = round((time.perf_counter() - start) * 1000, 2)
    response.headers["X-Request-ID"] = request_id

    logger.info(
      "request_completed", 
      request_id=request_id,
      method=request.method, 
      path=request.url.path, 
      status_code=response.status_code,
      duration_ms=duration_ms
    )

    return response