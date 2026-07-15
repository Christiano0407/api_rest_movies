from __future__ import annotations

from collections.abc import Callable

import structlog
from fastapi import Request
from slowapi import Limiter
from slowapi.util import get_remote_address

from app.core.config import settings

logger = structlog.get_logger(__name__)


def get_rate_limit_for_role(role: str) -> str:
    limits = settings.RATE_LIMITS_PER_MINUTE
    limit = limits.get(role, settings.RATE_LIMIT_AUTH)
    return f"{limit}/minute"


def role_based_rate_limit(role: str) -> Callable[[Callable], Callable]:
    limit_str = get_rate_limit_for_role(role)
    return limiter.limit(limit_str)


def get_rate_limit_remaining(request: Request) -> int:
    remaining = getattr(request.state, "view_rate_limit", None)
    if remaining is not None:
        return max(int(remaining), 0)
    return 0


limiter = Limiter(
    key_func=get_remote_address,
    storage_uri=settings.REDIS_URL,
)
