from fastapi import APIRouter
from app.api.v1.endpoints import auth, health, users, parishioners

api_router = APIRouter()
api_router.include_router(health.router, prefix="/health", tags=["health"])
api_router.include_router(auth.router, prefix="/auth", tags=["authentication"])
api_router.include_router(users.router, prefix="/user-management", tags=["user management"])
api_router.include_router(parishioners.router, prefix="/parishioners", tags=['parishioner'])