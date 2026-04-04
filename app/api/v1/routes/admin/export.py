import csv
import io
import logging
import subprocess
from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, HTTPException, status
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import subqueryload

from app.api.deps import SessionDep, require_permission
from app.core.config import settings
from app.models.user import User as UserModel
from app.models.parishioner.core import Parishioner
from app.models.parishioner.related import FamilyInfo
from app.models.parishioner.core import ParishionerSacrament

logger = logging.getLogger(__name__)
router = APIRouter()

_REQUIRE = require_permission("admin:all")


@router.get("/db-dump", dependencies=[_REQUIRE])
async def download_db_dump() -> StreamingResponse:
    """
    Stream a pg_dump of the entire database. Super admin only.
    Requires pg_dump to be available in the container PATH.
    """
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
        "-F", "c",   # custom format (compressed, restorable with pg_restore)
    ]

    try:
        result = subprocess.run(
            cmd,
            env={**__import__("os").environ, **env},
            capture_output=True,
            timeout=120,
        )
    except FileNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="pg_dump not found. Ensure postgresql-client is installed in the container.",
        )
    except subprocess.TimeoutExpired:
        raise HTTPException(
            status_code=status.HTTP_504_GATEWAY_TIMEOUT,
            detail="pg_dump timed out.",
        )

    if result.returncode != 0:
        logger.error("pg_dump failed: %s", result.stderr.decode())
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"pg_dump failed: {result.stderr.decode()[:500]}",
        )

    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    filename = f"{settings.POSTGRES_DB}_dump_{timestamp}.dump"

    return StreamingResponse(
        io.BytesIO(result.stdout),
        media_type="application/octet-stream",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get("/users-csv", dependencies=[_REQUIRE])
async def export_users_csv(session: SessionDep) -> StreamingResponse:
    """
    Export all users as a CSV file. Super admin only.
    """
    users = session.query(UserModel).order_by(UserModel.created_at).all()

    output = io.StringIO()
    writer = csv.writer(output)

    writer.writerow([
        "id",
        "full_name",
        "email",
        "phone",
        "status",
        "login_method",
        "global_role",
        "church_units",
        "created_at",
        "updated_at",
    ])

    for user in users:
        units = "; ".join(
            f"{m.church_unit.name} ({m.role.name if m.role else 'no role'})"
            for m in (user.unit_memberships or [])
            if m.church_unit
        )
        writer.writerow([
            str(user.id),
            user.full_name,
            user.email,
            user.phone or "",
            user.status.value,
            user.login_method.value,
            user.role_ref.name if user.role_ref else "",
            units,
            user.created_at.isoformat() if user.created_at else "",
            user.updated_at.isoformat() if user.updated_at else "",
        ])

    output.seek(0)
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    filename = f"users_export_{timestamp}.csv"

    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get("/parishioners-csv", dependencies=[_REQUIRE])
async def export_parishioners_csv(session: SessionDep) -> StreamingResponse:
    """
    Export all parishioners with full detail (sacraments, societies, family,
    emergency contacts, medical conditions, occupation, skills, languages).
    Super admin only.
    """
    parishioners = (
        session.query(Parishioner)
        .options(
            subqueryload(Parishioner.church_unit),
            subqueryload(Parishioner.church_community),
            subqueryload(Parishioner.occupation_rel),
            subqueryload(Parishioner.family_info_rel).subqueryload(FamilyInfo.children_rel),
            subqueryload(Parishioner.emergency_contacts_rel),
            subqueryload(Parishioner.medical_conditions_rel),
            subqueryload(Parishioner.sacrament_records).subqueryload(ParishionerSacrament.sacrament),
            subqueryload(Parishioner.societies),
            subqueryload(Parishioner.skills_rel),
            subqueryload(Parishioner.languages_rel),
        )
        .order_by(Parishioner.last_name, Parishioner.first_name)
        .all()
    )

    output = io.StringIO()
    writer = csv.writer(output)

    writer.writerow([
        # ── Identity ──────────────────────────────────────
        "id", "old_church_id", "new_church_id",
        "title", "first_name", "last_name", "other_names",
        "maiden_name", "baptismal_name", "gender",
        "date_of_birth", "place_of_birth",
        "nationality", "hometown", "region", "country",
        "marital_status",
        # ── Contact ───────────────────────────────────────
        "mobile_number", "whatsapp_number", "email_address", "current_residence",
        # ── Vital ─────────────────────────────────────────
        "is_deceased", "date_of_death",
        # ── Status ────────────────────────────────────────
        "membership_status", "verification_status",
        "church_unit", "church_community",
        # ── Occupation ────────────────────────────────────
        "occupation_role", "occupation_employer",
        # ── Family ────────────────────────────────────────
        "spouse_name", "spouse_status", "spouse_phone",
        "father_name", "father_status",
        "mother_name", "mother_status",
        "children",
        # ── Emergency contacts ────────────────────────────
        "emergency_contacts",
        # ── Medical ───────────────────────────────────────
        "medical_conditions",
        # ── Sacraments ────────────────────────────────────
        "sacraments",
        # ── Societies ─────────────────────────────────────
        "societies",
        # ── Skills & Languages ────────────────────────────
        "skills", "languages",
        # ── Timestamps ────────────────────────────────────
        "created_at", "updated_at",
    ])

    def _sep(items):
        """Join a list of strings with ' | ' as multi-value separator."""
        return " | ".join(i for i in items if i)

    for p in parishioners:
        fam = p.family_info_rel
        occ = p.occupation_rel

        children = _sep([c.name for c in fam.children_rel]) if fam else ""

        emergency = _sep([
            f"{ec.name} ({ec.relationship}) {ec.primary_phone}"
            + (f"/{ec.alternative_phone}" if ec.alternative_phone else "")
            for ec in p.emergency_contacts_rel
        ])

        medical = _sep([mc.condition for mc in p.medical_conditions_rel])

        sacraments = _sep([
            f"{sr.sacrament.name}"
            + (f" on {sr.date_received.isoformat()}" if sr.date_received else "")
            + (f" at {sr.place}" if sr.place else "")
            + (f" by {sr.minister}" if sr.minister else "")
            for sr in p.sacrament_records
        ])

        societies = _sep([s.name for s in p.societies])
        skills = _sep([sk.name for sk in p.skills_rel])
        languages = _sep([lang.name for lang in p.languages_rel])

        writer.writerow([
            str(p.id),
            p.old_church_id or "",
            p.new_church_id or "",
            p.title or "",
            p.first_name,
            p.last_name,
            p.other_names or "",
            p.maiden_name or "",
            p.baptismal_name or "",
            p.gender.value if p.gender else "",
            p.date_of_birth.isoformat() if p.date_of_birth else "",
            p.place_of_birth or "",
            p.nationality or "",
            p.hometown or "",
            p.region or "",
            p.country or "",
            p.marital_status.value if p.marital_status else "",
            p.mobile_number or "",
            p.whatsapp_number or "",
            p.email_address or "",
            p.current_residence or "",
            "yes" if p.is_deceased else "no",
            p.date_of_death.isoformat() if p.date_of_death else "",
            p.membership_status.value if p.membership_status else "",
            p.verification_status.value if p.verification_status else "",
            p.church_unit.name if p.church_unit else "",
            p.church_community.name if p.church_community else "",
            occ.role if occ else "",
            occ.employer if occ else "",
            fam.spouse_name if fam else "",
            fam.spouse_status.value if fam and fam.spouse_status else "",
            fam.spouse_phone if fam else "",
            fam.father_name if fam else "",
            fam.father_status.value if fam and fam.father_status else "",
            fam.mother_name if fam else "",
            fam.mother_status.value if fam and fam.mother_status else "",
            children,
            emergency,
            medical,
            sacraments,
            societies,
            skills,
            languages,
            p.created_at.isoformat() if p.created_at else "",
            p.updated_at.isoformat() if p.updated_at else "",
        ])

    output.seek(0)
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    filename = f"parishioners_export_{timestamp}.csv"

    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
