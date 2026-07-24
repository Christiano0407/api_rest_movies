"""
Entry point of the FastAPI application.
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1.router import api_router
from app.core.config import settings
from app.core.exceptions import register_exception_handler
from app.core.logging import configure_logging
from app.middlewares.logging import RequestLoggingMiddlewares


def create_app() -> FastAPI:
  configure_logging(log_level=settings.LOG_LEVEL, environment=settings.ENVIRONMENT)

  app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    docs_url='/docs' if settings.docs_enable else None,
    redoc_url=None,
  )

  app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGIN,
    allow_credentials=settings.CORS_ALLOW_CREDENTIALS,
    allow_methods=['*'],
    allow_headers=['*'],
  )

  app.add_middleware(RequestLoggingMiddlewares)

  register_exception_handler(app)

  app.include_router(api_router, prefix=settings.API_V1_PREFIX)

  return app


app = create_app()
