from fastapi import APIRouter
from app.api.v1.routes import auth, health, users, statistics
from app.api.v1.routes.parishioner_routes import parishioners
from app.api.v1.routes import society
from app.api.v1.routes import sacrament
from app.api.v1.routes import church_community
from app.api.v1.routes import place_of_worship


api_router = APIRouter()
api_router.include_router(health.router, prefix="/health", tags=["health"])
api_router.include_router(users.router, prefix="/user-management", tags=["user management"])
api_router.include_router(auth.router, prefix="/auth", tags=["authentication"])

api_router.include_router(sacrament.router, prefix="/sacraments", tags=["sacrament"])
api_router.include_router(place_of_worship.router, prefix="/place-of-worship", tags=["place of worship"])
api_router.include_router(church_community.router, prefix="/church-community", tags=["church communities"])

api_router.include_router(parishioners.router, prefix="/parishioners", tags=['parishioner'])
api_router.include_router(society.router, prefix="/societies", tags=["societies"])
api_router.include_router(statistics.router, prefix="/statistics", tags=["statistics"])



