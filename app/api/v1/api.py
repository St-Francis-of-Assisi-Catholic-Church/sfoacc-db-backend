from fastapi import APIRouter
from app.api.v1.routes import auth, health, users, statistics
from app.api.v1.routes.parishioner_routes import parishioners


api_router = APIRouter()
api_router.include_router(health.router, prefix="/health", tags=["health"])
api_router.include_router(auth.router, prefix="/auth", tags=["authentication"])
api_router.include_router(users.router, prefix="/user-management", tags=["user management"])
api_router.include_router(parishioners.router, prefix="/parishioners", tags=['parishioner'])
api_router.include_router(statistics.router, prefix="/statistics", tags=["statistics"])