import logging
from fastapi import APIRouter
from app.api.v1.routes.parishioner_routes.file_upload import file_upload_router


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

router = APIRouter()


# file upload
router.include_router(
file_upload_router,
prefix="/parishioners",
# tags=["Uploads Parishioner"]
)
