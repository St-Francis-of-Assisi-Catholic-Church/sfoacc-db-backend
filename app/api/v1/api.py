from fastapi import APIRouter
from app.api.v1.routes import auth, health, users, statistics
from app.api.v1.routes.parishioners import router as parishioners_module
from app.api.v1.routes.societies import router as societies_module
from app.api.v1.routes.reference import languages, sacraments, church_community, place_of_worship
from app.api.v1.routes.messaging import router as messaging_module


api_router = APIRouter()
api_router.include_router(health.router, prefix="/health", tags=["health"])
api_router.include_router(users.router, prefix="/user-management", tags=["user management"])
api_router.include_router(auth.router, prefix="/auth", tags=["authentication"])

api_router.include_router(languages.router, prefix="/languages", tags=["Languages"])
api_router.include_router(sacraments.router, prefix="/sacraments", tags=["sacrament"])
api_router.include_router(place_of_worship.router, prefix="/place-of-worship", tags=["place of worship"])
api_router.include_router(church_community.router, prefix="/church-community", tags=["church communities"])

api_router.include_router(parishioners_module.router, prefix="/parishioners", tags=['parishioner'])
api_router.include_router(societies_module.router, prefix="/societies", tags=["societies"])
api_router.include_router(statistics.router, prefix="/statistics", tags=["statistics"])

api_router.include_router(messaging_module.router, prefix="/bulk-message", tags=["Bulk Messaging"])
