from typing import Literal
from uuid import UUID

from fastapi import APIRouter, HTTPException, Query, status
from fastapi.responses import Response
from sqlalchemy.orm import joinedload

from app.api.deps import SessionDep, CurrentUser, require_permission
from app.models.parishioner import Parishioner as ParishionerModel, FamilyInfo, ParishionerSacrament
from app.services.report.generator import ParishionerReportGenerator

report_router = APIRouter()


def _load_parishioner(session, parishioner_id: UUID):
    return (
        session.query(ParishionerModel)
        .options(
            joinedload(ParishionerModel.occupation_rel),
            joinedload(ParishionerModel.family_info_rel).joinedload(FamilyInfo.children_rel),
            joinedload(ParishionerModel.emergency_contacts_rel),
            joinedload(ParishionerModel.medical_conditions_rel),
            joinedload(ParishionerModel.sacrament_records).joinedload(ParishionerSacrament.sacrament),
            joinedload(ParishionerModel.skills_rel),
            joinedload(ParishionerModel.languages_rel),
            joinedload(ParishionerModel.societies),
            joinedload(ParishionerModel.church_unit),
            joinedload(ParishionerModel.church_community),
        )
        .filter(ParishionerModel.id == parishioner_id)
        .first()
    )


@report_router.get(
    "",
    dependencies=[require_permission("parishioner:read")],
    summary="Download a full parishioner report as PDF or CSV",
)
def download_report(
    parishioner_id: UUID,
    session: SessionDep,
    current_user: CurrentUser,
    format: Literal["pdf", "csv"] = Query("pdf", description="Report format: pdf or csv"),
):
    parishioner = _load_parishioner(session, parishioner_id)

    if not parishioner:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Parishioner not found")

    name_slug = f"{parishioner.first_name}_{parishioner.last_name}".replace(" ", "_")

    if format == "csv":
        content = ParishionerReportGenerator.generate_csv(parishioner, session)
        return Response(
            content=content,
            media_type="text/csv",
            headers={"Content-Disposition": f'attachment; filename="{name_slug}_report.csv"'},
        )

    # PDF
    try:
        content = ParishionerReportGenerator.generate_pdf(parishioner, session)
    except RuntimeError as e:
        raise HTTPException(status_code=status.HTTP_501_NOT_IMPLEMENTED, detail=str(e))

    return Response(
        content=content,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{name_slug}_report.pdf"'},
    )
