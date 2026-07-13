from collections.abc import AsyncIterator
from redis.asyncio import ConnectionPool, Redis
from app.core.config import settings


# ==== Connection DB  - Caché 
_pool = ConnectionPool.from_url(settings.REDIS_URL, decode_response=True)

# ==== Redis connect with DB 
def get_redis_connection() -> Redis:
  return Redis(connection_pool=_pool)

# ==== Connection / DB - Caché  | Close conn
async def get_redis() -> AsyncIterator[Redis]: 
  conn = get_redis_connection()
  try:
    yield conn
  finally: 
    await conn.aclose()