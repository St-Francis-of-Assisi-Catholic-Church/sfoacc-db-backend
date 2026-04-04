import io
import csv
from datetime import datetime
from typing import Any, Optional

from app.models.parishioner import Parishioner as ParishionerModel
from app.models.society import society_members
from sqlalchemy import select
from sqlalchemy.orm import Session


def _fmt_date(value: Any) -> str:
    if value is None:
        return ""
    if hasattr(value, "strftime"):
        return value.strftime("%d %B, %Y")
    return str(value)


def _fmt_enum(value: Any) -> str:
    if value is None:
        return ""
    if hasattr(value, "value"):
        return value.value
    return str(value)


class ParishionerReportGenerator:

    @staticmethod
    def generate_csv(parishioner: ParishionerModel, session: Session) -> bytes:
        output = io.StringIO()
        writer = csv.writer(output)

        # Resolve multi-valued fields into readable strings
        occ = parishioner.occupation_rel
        fam = parishioner.family_info_rel
        children_str = (
            " | ".join(c.name for c in fam.children_rel)
            if fam and fam.children_rel else ""
        )

        ec_parts = []
        for ec in (parishioner.emergency_contacts_rel or []):
            phone = ec.primary_phone or ""
            alt = f" / {ec.alternative_phone}" if ec.alternative_phone else ""
            ec_parts.append(f"{ec.name or ''} ({ec.relationship or ''}) {phone}{alt}")
        emergency_contacts_str = " | ".join(ec_parts)

        medical_str = " | ".join(
            mc.condition or "" for mc in (parishioner.medical_conditions_rel or [])
        )

        sacraments_str = " | ".join(
            f"{(rec.sacrament.name if rec.sacrament else '')} ({_fmt_date(rec.date_received)})"
            for rec in (parishioner.sacrament_records or [])
        )

        societies_str = ""
        if parishioner.societies:
            membership_rows = session.execute(
                select(society_members).where(society_members.c.parishioner_id == parishioner.id)
            ).mappings().all()
            membership_map = {row["society_id"]: row for row in membership_rows}
            societies_str = " | ".join(
                f"{soc.name} ({_fmt_enum(membership_map.get(soc.id, {}).get('membership_status'))})"
                for soc in parishioner.societies
            )

        skills_str = " | ".join(s.name for s in (parishioner.skills_rel or []))
        langs_str = " | ".join(l.name for l in (parishioner.languages_rel or []))

        headers = [
            "System ID", "Old Church ID", "New Church ID",
            "Title", "First Name", "Other Names", "Last Name", "Maiden Name", "Baptismal Name",
            "Gender", "Date of Birth", "Place of Birth", "Nationality",
            "Hometown", "Region", "Country",
            "Marital Status", "Is Deceased", "Date of Death",
            "Mobile Number", "WhatsApp Number", "Email Address", "Current Residence",
            "Church Unit", "Church Community", "Membership Status", "Verification Status",
            "Occupation Role", "Employer",
            "Spouse Name", "Spouse Status", "Spouse Phone",
            "Father Name", "Father Status", "Mother Name", "Mother Status", "Children",
            "Emergency Contacts",
            "Medical Conditions",
            "Sacraments",
            "Societies",
            "Skills", "Languages Spoken",
            "Record Created", "Last Updated",
        ]

        values = [
            str(parishioner.id), parishioner.old_church_id or "", parishioner.new_church_id or "",
            parishioner.title or "", parishioner.first_name, parishioner.other_names or "",
            parishioner.last_name, parishioner.maiden_name or "", parishioner.baptismal_name or "",
            _fmt_enum(parishioner.gender), _fmt_date(parishioner.date_of_birth),
            parishioner.place_of_birth or "", parishioner.nationality or "",
            parishioner.hometown or "", parishioner.region or "", parishioner.country or "",
            _fmt_enum(parishioner.marital_status),
            "Yes" if parishioner.is_deceased else "No", _fmt_date(parishioner.date_of_death),
            parishioner.mobile_number or "", parishioner.whatsapp_number or "",
            parishioner.email_address or "", parishioner.current_residence or "",
            parishioner.church_unit.name if parishioner.church_unit else "",
            parishioner.church_community.name if parishioner.church_community else "",
            _fmt_enum(parishioner.membership_status), _fmt_enum(parishioner.verification_status),
            occ.role if occ else "", occ.employer if occ else "",
            fam.spouse_name if fam else "", fam.spouse_status if fam else "",
            fam.spouse_phone if fam else "",
            fam.father_name if fam else "", _fmt_enum(fam.father_status if fam else None),
            fam.mother_name if fam else "", _fmt_enum(fam.mother_status if fam else None),
            children_str,
            emergency_contacts_str,
            medical_str,
            sacraments_str,
            societies_str,
            skills_str, langs_str,
            _fmt_date(parishioner.created_at), _fmt_date(parishioner.updated_at),
        ]

        writer.writerow(headers)
        writer.writerow(values)

        return output.getvalue().encode("utf-8-sig")  # utf-8-sig for Excel compatibility

    @staticmethod
    def generate_pdf(parishioner: ParishionerModel, session: Session) -> bytes:
        try:
            from weasyprint import HTML
        except ImportError:
            raise RuntimeError("weasyprint is not installed. Run: pip install weasyprint")

        from app.services.report.pdf_template import REPORT_PDF_TEMPLATE

        def field(label: str, value: Any, badge_class: str = "") -> str:
            if value is None or value == "":
                val_html = '<span class="na">N/A</span>'
            elif badge_class:
                val_html = f'<span class="badge {badge_class}">{value}</span>'
            else:
                val_html = str(value)
            return (
                f'<div class="field-row">'
                f'<div class="field-label">{label}</div>'
                f'<div class="field-value">{val_html}</div>'
                f'</div>'
            )

        def table(headers: list, rows: list) -> str:
            ths = "".join(f"<th>{h}</th>" for h in headers)
            trs = ""
            for row in rows:
                tds = "".join(f"<td>{cell or '—'}</td>" for cell in row)
                trs += f"<tr>{tds}</tr>"
            return (
                f'<table class="data-table"><thead><tr>{ths}</tr></thead>'
                f"<tbody>{trs}</tbody></table>"
            )

        def section(title: str, content: str) -> str:
            return (
                f'<div class="section">'
                f'<div class="section-title">{title}</div>'
                f"{content}"
                f"</div>"
            )

        # ── Personal ──────────────────────────────────────────────────────────
        ms_badge = {
            "active": "badge-active",
            "deceased": "badge-deceased",
        }.get(_fmt_enum(parishioner.membership_status).lower(), "badge-default")

        vs_badge = {
            "verified": "badge-verified",
            "pending": "badge-pending",
        }.get(_fmt_enum(parishioner.verification_status).lower(), "badge-default")

        personal_fields = (
            field("Title", parishioner.title)
            + field("First Name", parishioner.first_name)
            + field("Other Names", parishioner.other_names)
            + field("Last Name", parishioner.last_name)
            + field("Maiden Name", parishioner.maiden_name)
            + field("Baptismal Name", parishioner.baptismal_name)
            + field("Gender", _fmt_enum(parishioner.gender))
            + field("Date of Birth", _fmt_date(parishioner.date_of_birth))
            + field("Place of Birth", parishioner.place_of_birth)
            + field("Nationality", parishioner.nationality)
            + field("Hometown", parishioner.hometown)
            + field("Region", parishioner.region)
            + field("Country", parishioner.country)
            + field("Marital Status", _fmt_enum(parishioner.marital_status))
            + field("Deceased", "Yes" if parishioner.is_deceased else "No")
            + field("Date of Death", _fmt_date(parishioner.date_of_death))
        )

        # ── Contact ───────────────────────────────────────────────────────────
        contact_fields = (
            field("Mobile", parishioner.mobile_number)
            + field("WhatsApp", parishioner.whatsapp_number)
            + field("Email", parishioner.email_address)
            + field("Residence", parishioner.current_residence)
        )

        # ── Church ────────────────────────────────────────────────────────────
        church_fields = (
            field("Church Unit", parishioner.church_unit.name if parishioner.church_unit else None)
            + field("Church Community", parishioner.church_community.name if parishioner.church_community else None)
            + field("Membership Status", _fmt_enum(parishioner.membership_status), ms_badge)
            + field("Verification Status", _fmt_enum(parishioner.verification_status), vs_badge)
            + field("Record Created", _fmt_date(parishioner.created_at))
            + field("Last Updated", _fmt_date(parishioner.updated_at))
        )

        # ── Occupation ────────────────────────────────────────────────────────
        occ = parishioner.occupation_rel
        occupation_fields = (
            field("Role", occ.role if occ else None)
            + field("Employer", occ.employer if occ else None)
        )

        # ── Family ────────────────────────────────────────────────────────────
        fam = parishioner.family_info_rel
        if fam:
            children = ", ".join(c.name for c in fam.children_rel) if fam.children_rel else None
            family_fields = (
                field("Spouse Name", fam.spouse_name)
                + field("Spouse Status", fam.spouse_status)
                + field("Spouse Phone", fam.spouse_phone)
                + field("Father's Name", fam.father_name)
                + field("Father's Status", _fmt_enum(fam.father_status))
                + field("Mother's Name", fam.mother_name)
                + field("Mother's Status", _fmt_enum(fam.mother_status))
                + field("Children", children)
            )
        else:
            family_fields = field("Family Info", None)

        # ── Emergency Contacts ────────────────────────────────────────────────
        if parishioner.emergency_contacts_rel:
            ec_table = table(
                ["Name", "Relationship", "Primary Phone", "Alt. Phone"],
                [
                    [ec.name, ec.relationship, ec.primary_phone, ec.alternative_phone]
                    for ec in parishioner.emergency_contacts_rel
                ],
            )
            emergency_contacts_section = section("Emergency Contacts", ec_table)
        else:
            emergency_contacts_section = section(
                "Emergency Contacts",
                '<p style="color:#aaa;font-style:italic;font-size:8.5pt">No emergency contacts on record</p>',
            )

        # ── Medical ───────────────────────────────────────────────────────────
        if parishioner.medical_conditions_rel:
            med_table = table(
                ["Condition", "Notes"],
                [[mc.condition, mc.notes] for mc in parishioner.medical_conditions_rel],
            )
            medical_section = section("Medical Conditions", med_table)
        else:
            medical_section = section(
                "Medical Conditions",
                '<p style="color:#aaa;font-style:italic;font-size:8.5pt">No medical conditions on record</p>',
            )

        # ── Sacraments ────────────────────────────────────────────────────────
        if parishioner.sacrament_records:
            sac_table = table(
                ["Sacrament", "Date Received", "Place", "Minister", "Notes"],
                [
                    [
                        rec.sacrament.name if rec.sacrament else "—",
                        _fmt_date(rec.date_received),
                        rec.place,
                        rec.minister,
                        rec.notes,
                    ]
                    for rec in parishioner.sacrament_records
                ],
            )
            sacraments_section = section("Sacraments", sac_table)
        else:
            sacraments_section = section(
                "Sacraments",
                '<p style="color:#aaa;font-style:italic;font-size:8.5pt">No sacrament records</p>',
            )

        # ── Societies ─────────────────────────────────────────────────────────
        if parishioner.societies:
            membership_rows = session.execute(
                select(society_members).where(society_members.c.parishioner_id == parishioner.id)
            ).mappings().all()
            membership_map = {row["society_id"]: row for row in membership_rows}

            soc_table = table(
                ["Society", "Status", "Date Joined"],
                [
                    [
                        soc.name,
                        _fmt_enum(membership_map.get(soc.id, {}).get("membership_status")),
                        _fmt_date(membership_map.get(soc.id, {}).get("join_date")),
                    ]
                    for soc in parishioner.societies
                ],
            )
            societies_section = section("Societies", soc_table)
        else:
            societies_section = section(
                "Societies",
                '<p style="color:#aaa;font-style:italic;font-size:8.5pt">No society memberships</p>',
            )

        # ── Skills & Languages ────────────────────────────────────────────────
        skills = ", ".join(s.name for s in parishioner.skills_rel) if parishioner.skills_rel else None
        langs = ", ".join(l.name for l in parishioner.languages_rel) if parishioner.languages_rel else None
        skills_fields = field("Skills", skills) + field("Languages Spoken", langs)

        full_name = f"{parishioner.first_name} {parishioner.other_names or ''} {parishioner.last_name}".strip()
        full_name = " ".join(full_name.split())

        html_content = REPORT_PDF_TEMPLATE.format(
            full_name=full_name,
            new_church_id=parishioner.new_church_id or "—",
            old_church_id=parishioner.old_church_id or "—",
            system_id=str(parishioner.id),
            generated_at=datetime.now().strftime("%d %B %Y, %H:%M"),
            personal_fields=personal_fields,
            contact_fields=contact_fields,
            church_fields=church_fields,
            occupation_fields=occupation_fields,
            family_fields=family_fields,
            emergency_contacts_section=emergency_contacts_section,
            medical_section=medical_section,
            sacraments_section=sacraments_section,
            societies_section=societies_section,
            skills_fields=skills_fields,
        )

        return HTML(string=html_content).write_pdf()
