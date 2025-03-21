from fastapi import APIRouter
from app.api.v1.endpoints import auth, health, users

api_router = APIRouter()
api_router.include_router(health.router, prefix="/health", tags=["health"])
api_router.include_router(auth.router, prefix="/auth", tags=["authentication"])
api_router.include_router(users.router, prefix="/user-management", tags=["user management"])