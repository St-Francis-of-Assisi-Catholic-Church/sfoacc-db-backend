from fastapi import APIRouter
from app.api.v1.routes import auth, health, users, statistics
from app.api.v1.routes.parishioners import router as parishioners_module
from app.api.v1.routes.societies import router as societies_module
from app.api.v1.routes.reference import languages, sacraments, church_community
from app.api.v1.routes.messaging import router as messaging_module
from app.api.v1.routes.parish import router as parish_module
from app.api.v1.routes.admin import rbac as admin_rbac_module
from app.api.v1.routes.admin import settings as admin_settings_module
from app.api.v1.routes.admin import audit as admin_audit_module
from app.api.v1.routes.admin import export as admin_export_module
from app.api.v1.routes import guide as guide_module
from app.api.v1.routes import app_info as app_info_module
from app.api.v1.routes.events.router import router as events_router


api_router = APIRouter()
api_router.include_router(health.router, prefix="/health", tags=["health"])
api_router.include_router(app_info_module.router, prefix="/app", tags=["app info"])
api_router.include_router(users.router, prefix="/user-management", tags=["user management"])
api_router.include_router(auth.router, prefix="/auth", tags=["authentication"])

api_router.include_router(languages.router, prefix="/languages", tags=["Languages"])
api_router.include_router(sacraments.router, prefix="/sacraments", tags=["sacrament"])
api_router.include_router(church_community.router, prefix="/church-community", tags=["church communities"])

api_router.include_router(parishioners_module.router, prefix="/parishioners", tags=['parishioner'])
api_router.include_router(societies_module.router, prefix="/societies", tags=["societies"])
api_router.include_router(statistics.router, prefix="/statistics", tags=["statistics"])

api_router.include_router(messaging_module.router, prefix="/bulk-message", tags=["Bulk Messaging"])

api_router.include_router(parish_module.router, prefix="/parish", tags=["parish"])
api_router.include_router(admin_rbac_module.router, prefix="/admin", tags=["admin"])
api_router.include_router(admin_settings_module.router, prefix="/admin/settings", tags=["admin"])
api_router.include_router(admin_audit_module.router, prefix="/admin/audit-logs", tags=["admin"])
api_router.include_router(admin_export_module.router, prefix="/admin/export", tags=["admin"])

api_router.include_router(events_router, prefix="/events", tags=["events"])

api_router.include_router(guide_module.router, tags=["docs"])
