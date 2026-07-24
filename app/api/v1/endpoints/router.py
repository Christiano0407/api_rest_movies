"""
app/api/v1/endpoints router.py — ensambla los 3 routers
"""
from fastapi import APIRouter

from app.api.v1.endpoints import account, auth, cinema, tmdb



api_router = APIRouter()
api_router.include_router(auth.router)
api_router.include_router(cinema.router)
api_router.include_router(tmdb.router)
api_router.include_router(account.router)