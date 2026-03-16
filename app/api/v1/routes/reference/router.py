from app.api.v1.routes.reference import languages, sacraments, church_community

# Re-export all routers for use in api.py
languages_router = languages.router
sacraments_router = sacraments.router
church_community_router = church_community.router
