import subprocess
import logging
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
import io

from app.api.deps import get_current_active_superuser
from app.core.config import settings

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get(
    "/download",
    summary="Download full database SQL dump",
    dependencies=[Depends(get_current_active_superuser)],
)
def download_db_dump():
    """
    Runs pg_dump and streams the result as a downloadable .sql file.
    Requires super admin privileges.
    """
    timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    filename = f"{settings.POSTGRES_DB}_dump_{timestamp}.sql"

    env = {
        "PGPASSWORD": settings.POSTGRES_PASSWORD,
    }

    cmd = [
        "pg_dump",
        "-h", settings.POSTGRES_SERVER,
        "-p", str(settings.POSTGRES_PORT),
        "-U", settings.POSTGRES_USER,
        "-d", settings.POSTGRES_DB,
        "--no-password",
    ]

    try:
        result = subprocess.run(
            cmd,
            env=env,
            capture_output=True,
        )
    except FileNotFoundError:
        logger.error("pg_dump not found on the server")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="pg_dump is not available on this server.",
        )

    if result.returncode != 0:
        logger.error("pg_dump failed: %s", result.stderr.decode())
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Database dump failed.",
        )

    sql_bytes = result.stdout

    return StreamingResponse(
        io.BytesIO(sql_bytes),
        media_type="application/octet-stream",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
