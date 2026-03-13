from app.api.v1.routes.reference import languages, sacraments, church_community, place_of_worship

# Re-export all routers for use in api.py
languages_router = languages.router
sacraments_router = sacraments.router
church_community_router = church_community.router
place_of_worship_router = place_of_worship.router
