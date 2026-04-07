#!/usr/bin/env python3
"""
Load parishioners and all related data from the SQL dump file into the current DB.

Run via Make or directly:
    docker compose exec api python3 /app/app/scripts/load_from_dump.py

What it does:
  1. Parses each COPY block from the dump
  2. Builds ID-remapping tables for church_communities, languages, societies,
     sacraments, and par_skills (all of which may have different PKs in the
     current DB)
  3. Loads in FK-safe order:
       par_skills → parishioners → par_family → par_children →
       par_emergency_contacts → par_medical_conditions → par_occupations →
       par_languages → par_parishioner_skills → par_sacraments →
       par_society_members
  4. Converts UPPERCASE enum values from the old schema to lowercase
  5. Uses ON CONFLICT DO NOTHING so re-running is safe
"""

from __future__ import annotations

import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, ROOT)

import logging
from typing import Any

logging.basicConfig(level=logging.INFO, format="%(levelname)s  %(message)s")
logger = logging.getLogger("load_from_dump")

_default_dump = "app_dump_20260310_075402.sql"
_dump_file = sys.argv[1] if len(sys.argv) > 1 else _default_dump
DUMP_PATH = os.path.join(ROOT, "dumps", _dump_file)

# ── Enum normalisation ────────────────────────────────────────────────────────
# PostgreSQL enums use UPPERCASE labels. The dump is mostly uppercase but some
# rows (added later) use lowercase. Uppercase everything to be safe.

_ENUM_COLS = {
    "membership_status", "verification_status", "gender",
    "marital_status", "spouse_status", "father_status", "mother_status",
    "meeting_frequency", "role",
}


def _norm(col: str, val: str | None) -> str | None:
    if val is None:
        return None
    if col in _ENUM_COLS:
        return val.upper()
    return val


# ── Dump parser ───────────────────────────────────────────────────────────────

def parse_copy_blocks(path: str) -> dict[str, list[dict[str, Any]]]:
    """
    Return {table_name: [row_dict, ...]} for every COPY block in the dump.
    NULL values (backslash-N) are converted to Python None.
    """
    blocks: dict[str, list[dict[str, Any]]] = {}
    current_table: str | None = None
    current_cols: list[str] = []
    in_copy = False

    with open(path, encoding="utf-8") as fh:
        for line in fh:
            line = line.rstrip("\n")

            if line.startswith("COPY public.") and "FROM stdin" in line:
                # e.g. COPY public.parishioners (col1, col2, ...) FROM stdin;
                rest = line[len("COPY public."):]
                table_part, cols_part = rest.split("(", 1)
                current_table = table_part.strip()
                cols_part = cols_part.split(")")[0]
                current_cols = [c.strip() for c in cols_part.split(",")]
                blocks[current_table] = []
                in_copy = True
                continue

            if in_copy:
                if line == "\\.":
                    in_copy = False
                    current_table = None
                    continue
                fields = line.split("\t")
                row: dict[str, Any] = {}
                for col, val in zip(current_cols, fields):
                    row[col] = None if val == "\\N" else val
                blocks[current_table].append(row)

    return blocks


# ── Helpers ───────────────────────────────────────────────────────────────────

def _execute_batch(conn, sql: str, rows: list[dict], table: str) -> int:
    if not rows:
        logger.info(f"  {table}: no rows to insert")
        return 0
    from sqlalchemy import text as sa_text
    inserted = 0
    skipped = 0
    for row in rows:
        sp = conn.begin_nested()  # savepoint — rollback only this row on error
        try:
            conn.execute(sa_text(sql), row)
            sp.commit()
            inserted += 1
        except Exception as e:
            sp.rollback()
            skipped += 1
            if skipped <= 3:  # only log first few to avoid noise
                msg = str(e).split("\n")[0]
                logger.warning(f"  {table}: skipped row — {msg}")
    conn.commit()
    if skipped > 3:
        logger.warning(f"  {table}: ... and {skipped - 3} more skipped rows")
    logger.info(f"  {table}: {inserted}/{len(rows)} rows inserted  ({skipped} skipped)")
    return inserted


# ── Main ──────────────────────────────────────────────────────────────────────

def main() -> None:
    from sqlalchemy import text
    from app.core.database import db

    db.init_app()

    logger.info(f"Parsing dump: {DUMP_PATH}")
    blocks = parse_copy_blocks(DUMP_PATH)
    logger.info(f"Found tables: {sorted(blocks.keys())}")

    with db.engine.connect() as conn:

        # ── Build ID remapping tables ─────────────────────────────────────────

        # church_communities: dump IDs → current DB IDs (matched by name)
        cc_rows = conn.execute(text("SELECT id, name FROM church_communities")).fetchall()
        cc_by_name = {r.name.strip().lower(): r.id for r in cc_rows}
        cc_id_map: dict[str, int | None] = {}
        for r in blocks.get("church_communities", []):
            old_id = r["id"]
            name = (r["name"] or "").strip().lower()
            cc_id_map[old_id] = cc_by_name.get(name)
        logger.info(f"church_community id map: {len(cc_id_map)} entries, "
                    f"{sum(1 for v in cc_id_map.values() if v is None)} unmapped")

        # languages: dump IDs → current DB IDs (matched by name)
        lang_rows = conn.execute(text("SELECT id, name FROM languages")).fetchall()
        lang_by_name = {r.name.strip().lower(): r.id for r in lang_rows}
        lang_id_map: dict[str, int | None] = {}
        for r in blocks.get("languages", []):
            old_id = r["id"]
            name = (r["name"] or "").strip().lower()
            lang_id_map[old_id] = lang_by_name.get(name)
        logger.info(f"language id map: {len(lang_id_map)} entries, "
                    f"{sum(1 for v in lang_id_map.values() if v is None)} unmapped")

        # societies: dump IDs → current DB IDs (matched by name)
        soc_rows = conn.execute(text("SELECT id, name FROM societies")).fetchall()
        soc_by_name = {r.name.strip().lower(): r.id for r in soc_rows}
        soc_id_map: dict[str, int | None] = {}
        for r in blocks.get("societies", []):
            old_id = r["id"]
            name = (r["name"] or "").strip().lower()
            soc_id_map[old_id] = soc_by_name.get(name)
        logger.info(f"society id map: {len(soc_id_map)} entries, "
                    f"{sum(1 for v in soc_id_map.values() if v is None)} unmapped")

        # sacraments: dump IDs → current DB IDs (matched by name)
        sac_rows = conn.execute(text("SELECT id, name FROM sacrament")).fetchall()
        sac_by_name = {r.name.strip().lower(): r.id for r in sac_rows}
        sac_id_map: dict[str, int | None] = {}
        for r in blocks.get("sacrament", []):
            old_id = r["id"]
            name = (r["name"] or "").strip().lower()
            sac_id_map[old_id] = sac_by_name.get(name)
        logger.info(f"sacrament id map: {len(sac_id_map)} entries")

        # par_skills: insert missing ones, then build old_id → current_id map
        logger.info("Loading par_skills...")
        skill_rows = conn.execute(text("SELECT id, name FROM par_skills")).fetchall()
        skill_by_name = {r.name.strip().lower(): r.id for r in skill_rows}
        skill_id_map: dict[str, int | None] = {}

        for r in blocks.get("par_skills", []):
            old_id = r["id"]
            name = (r["name"] or "").strip()
            existing = skill_by_name.get(name.lower())
            if existing:
                skill_id_map[old_id] = existing
            else:
                try:
                    result = conn.execute(
                        text("INSERT INTO par_skills (name, created_at, updated_at) "
                             "VALUES (:name, :created_at, :updated_at) "
                             "ON CONFLICT (name) DO NOTHING RETURNING id"),
                        {"name": name, "created_at": r["created_at"], "updated_at": r["updated_at"]},
                    ).fetchone()
                    if result:
                        new_id = result[0]
                    else:
                        # Conflict: fetch existing
                        new_id = conn.execute(
                            text("SELECT id FROM par_skills WHERE name = :name"), {"name": name}
                        ).scalar()
                    skill_id_map[old_id] = new_id
                    skill_by_name[name.lower()] = new_id
                except Exception as e:
                    logger.warning(f"  par_skills: failed to insert '{name}' — {e}")
                    skill_id_map[old_id] = None
        conn.commit()
        logger.info(f"  par_skills: {len(skill_id_map)} skills mapped")

        # ── 1. parishioners ───────────────────────────────────────────────────
        logger.info("Loading parishioners...")
        par_rows = []
        for r in blocks.get("parishioners", []):
            old_cc_id = r.get("church_community_id")
            new_cc_id = cc_id_map.get(old_cc_id) if old_cc_id else None

            par_rows.append({
                "id": r["id"],
                "old_church_id": r.get("old_church_id"),
                "new_church_id": r.get("new_church_id"),
                "membership_status": _norm("membership_status", r.get("membership_status")),
                "verification_status": _norm("verification_status", r.get("verification_status")),
                "first_name": r["first_name"],
                "last_name": r["last_name"],
                "other_names": r.get("other_names"),
                "maiden_name": r.get("maiden_name"),
                "gender": _norm("gender", r.get("gender")),
                "date_of_birth": r.get("date_of_birth"),
                "place_of_birth": r.get("place_of_birth"),
                "hometown": r.get("hometown"),
                "region": r.get("region"),
                "country": r.get("country"),
                "marital_status": _norm("marital_status", r.get("marital_status")),
                "mobile_number": r.get("mobile_number"),
                "whatsapp_number": r.get("whatsapp_number"),
                "email_address": r.get("email_address"),
                "current_residence": r.get("current_residence"),
                "church_community_id": new_cc_id,
                "church_unit_id": None,  # old schema had place_of_worship_id — not mapped
                "created_at": r["created_at"],
                "updated_at": r["updated_at"],
            })

        _execute_batch(conn, """
            INSERT INTO parishioners (
                id, old_church_id, new_church_id,
                membership_status, verification_status,
                first_name, last_name, other_names, maiden_name,
                gender, date_of_birth, place_of_birth,
                hometown, region, country, marital_status,
                mobile_number, whatsapp_number, email_address, current_residence,
                church_community_id, church_unit_id,
                created_at, updated_at
            ) VALUES (
                :id, :old_church_id, :new_church_id,
                :membership_status, :verification_status,
                :first_name, :last_name, :other_names, :maiden_name,
                :gender, :date_of_birth, :place_of_birth,
                :hometown, :region, :country, :marital_status,
                :mobile_number, :whatsapp_number, :email_address, :current_residence,
                :church_community_id, :church_unit_id,
                :created_at, :updated_at
            ) ON CONFLICT (id) DO NOTHING
        """, par_rows, "parishioners")

        # Build set of loaded parishioner UUIDs for FK safety
        loaded_ids = {r["id"] for r in par_rows}

        # ── 2. par_family ─────────────────────────────────────────────────────
        logger.info("Loading par_family...")
        family_rows = []
        for r in blocks.get("par_family", []):
            if r["parishioner_id"] not in loaded_ids:
                continue
            family_rows.append({
                "id": r["id"],
                "parishioner_id": r["parishioner_id"],
                "spouse_name": r.get("spouse_name"),
                "spouse_status": _norm("spouse_status", r.get("spouse_status")),
                "spouse_phone": r.get("spouse_phone"),
                "father_name": r.get("father_name"),
                "father_status": _norm("father_status", r.get("father_status")),
                "mother_name": r.get("mother_name"),
                "mother_status": _norm("mother_status", r.get("mother_status")),
                "created_at": r["created_at"],
                "updated_at": r["updated_at"],
            })
        _execute_batch(conn, """
            INSERT INTO par_family (
                id, parishioner_id,
                spouse_name, spouse_status, spouse_phone,
                father_name, father_status, mother_name, mother_status,
                created_at, updated_at
            ) VALUES (
                :id, :parishioner_id,
                :spouse_name, :spouse_status, :spouse_phone,
                :father_name, :father_status, :mother_name, :mother_status,
                :created_at, :updated_at
            ) ON CONFLICT (id) DO NOTHING
        """, family_rows, "par_family")

        # Build family_info_id map old → confirm existence
        loaded_family_ids = {r["id"] for r in family_rows}

        # ── 3. par_children ───────────────────────────────────────────────────
        logger.info("Loading par_children...")
        child_rows = []
        for r in blocks.get("par_children", []):
            if r["family_info_id"] not in loaded_family_ids:
                continue
            child_rows.append({
                "id": r["id"],
                "family_info_id": r["family_info_id"],
                "name": r["name"],
                "created_at": r["created_at"],
                "updated_at": r["updated_at"],
            })
        _execute_batch(conn, """
            INSERT INTO par_children (id, family_info_id, name, created_at, updated_at)
            VALUES (:id, :family_info_id, :name, :created_at, :updated_at)
            ON CONFLICT (id) DO NOTHING
        """, child_rows, "par_children")

        # ── 4. par_emergency_contacts ─────────────────────────────────────────
        logger.info("Loading par_emergency_contacts...")
        ec_rows = []
        for r in blocks.get("par_emergency_contacts", []):
            if r["parishioner_id"] not in loaded_ids:
                continue
            ec_rows.append({
                "id": r["id"],
                "parishioner_id": r["parishioner_id"],
                "name": r["name"],
                "relationship": r["relationship"],
                "primary_phone": r["primary_phone"],
                "alternative_phone": r.get("alternative_phone"),
                "created_at": r["created_at"],
                "updated_at": r["updated_at"],
            })
        _execute_batch(conn, """
            INSERT INTO par_emergency_contacts
                (id, parishioner_id, name, relationship, primary_phone, alternative_phone, created_at, updated_at)
            VALUES
                (:id, :parishioner_id, :name, :relationship, :primary_phone, :alternative_phone, :created_at, :updated_at)
            ON CONFLICT (id) DO NOTHING
        """, ec_rows, "par_emergency_contacts")

        # ── 5. par_medical_conditions ─────────────────────────────────────────
        logger.info("Loading par_medical_conditions...")
        med_rows = []
        for r in blocks.get("par_medical_conditions", []):
            if r["parishioner_id"] not in loaded_ids:
                continue
            med_rows.append({
                "id": r["id"],
                "parishioner_id": r["parishioner_id"],
                "condition": r["condition"],
                "notes": r.get("notes"),
                "created_at": r["created_at"],
                "updated_at": r["updated_at"],
            })
        _execute_batch(conn, """
            INSERT INTO par_medical_conditions (id, parishioner_id, condition, notes, created_at, updated_at)
            VALUES (:id, :parishioner_id, :condition, :notes, :created_at, :updated_at)
            ON CONFLICT (id) DO NOTHING
        """, med_rows, "par_medical_conditions")

        # ── 6. par_occupations ────────────────────────────────────────────────
        logger.info("Loading par_occupations...")
        occ_rows = []
        for r in blocks.get("par_occupations", []):
            if r["parishioner_id"] not in loaded_ids:
                continue
            occ_rows.append({
                "id": r["id"],
                "parishioner_id": r["parishioner_id"],
                "role": r["role"],
                "employer": r["employer"],
                "created_at": r["created_at"],
                "updated_at": r["updated_at"],
            })
        _execute_batch(conn, """
            INSERT INTO par_occupations (id, parishioner_id, role, employer, created_at, updated_at)
            VALUES (:id, :parishioner_id, :role, :employer, :created_at, :updated_at)
            ON CONFLICT (id) DO NOTHING
        """, occ_rows, "par_occupations")

        # ── 7. par_languages ──────────────────────────────────────────────────
        logger.info("Loading par_languages...")
        pl_rows = []
        for r in blocks.get("par_languages", []):
            if r["parishioner_id"] not in loaded_ids:
                continue
            new_lang_id = lang_id_map.get(r["language_id"])
            if new_lang_id is None:
                continue
            pl_rows.append({
                "parishioner_id": r["parishioner_id"],
                "language_id": new_lang_id,
                "created_at": r["created_at"],
                "updated_at": r["updated_at"],
            })
        _execute_batch(conn, """
            INSERT INTO par_languages (parishioner_id, language_id, created_at, updated_at)
            VALUES (:parishioner_id, :language_id, :created_at, :updated_at)
            ON CONFLICT DO NOTHING
        """, pl_rows, "par_languages")

        # ── 8. par_parishioner_skills ─────────────────────────────────────────
        logger.info("Loading par_parishioner_skills...")
        ps_rows = []
        for r in blocks.get("par_parishioner_skills", []):
            if r["parishioner_id"] not in loaded_ids:
                continue
            new_skill_id = skill_id_map.get(r["skill_id"])
            if new_skill_id is None:
                continue
            ps_rows.append({
                "parishioner_id": r["parishioner_id"],
                "skill_id": new_skill_id,
                "created_at": r["created_at"],
                "updated_at": r["updated_at"],
            })
        _execute_batch(conn, """
            INSERT INTO par_parishioner_skills (parishioner_id, skill_id, created_at, updated_at)
            VALUES (:parishioner_id, :skill_id, :created_at, :updated_at)
            ON CONFLICT DO NOTHING
        """, ps_rows, "par_parishioner_skills")

        # ── 9. par_sacraments ─────────────────────────────────────────────────
        logger.info("Loading par_sacraments...")
        sacrament_rows = []
        for r in blocks.get("par_sacraments", []):
            if r["parishioner_id"] not in loaded_ids:
                continue
            new_sac_id = sac_id_map.get(r["sacrament_id"])
            if new_sac_id is None:
                continue
            sacrament_rows.append({
                "id": r["id"],
                "parishioner_id": r["parishioner_id"],
                "sacrament_id": new_sac_id,
                "date_received": r.get("date_received"),
                "place": r.get("place"),
                "minister": r.get("minister"),
                "notes": r.get("notes"),
                "created_at": r["created_at"],
                "updated_at": r["updated_at"],
            })
        _execute_batch(conn, """
            INSERT INTO par_sacraments
                (id, parishioner_id, sacrament_id, date_received, place, minister, notes, created_at, updated_at)
            VALUES
                (:id, :parishioner_id, :sacrament_id, :date_received, :place, :minister, :notes, :created_at, :updated_at)
            ON CONFLICT (id) DO NOTHING
        """, sacrament_rows, "par_sacraments")

        # ── 10. par_society_members ───────────────────────────────────────────
        logger.info("Loading par_society_members...")
        sm_rows = []
        for r in blocks.get("par_society_members", []):
            if r["parishioner_id"] not in loaded_ids:
                continue
            new_soc_id = soc_id_map.get(r["society_id"])
            if new_soc_id is None:
                continue
            sm_rows.append({
                "society_id": new_soc_id,
                "parishioner_id": r["parishioner_id"],
                "join_date": r.get("join_date"),
                "membership_status": r.get("membership_status"),
                "created_at": r["created_at"],
                "updated_at": r["updated_at"],
            })
        _execute_batch(conn, """
            INSERT INTO par_society_members (society_id, parishioner_id, join_date, membership_status, created_at, updated_at)
            VALUES (:society_id, :parishioner_id, :join_date, :membership_status, :created_at, :updated_at)
            ON CONFLICT DO NOTHING
        """, sm_rows, "par_society_members")

    # Final counts
    from sqlalchemy import text
    with db.engine.connect() as conn:
        total = conn.execute(text("SELECT COUNT(*) FROM parishioners")).scalar()
        logger.info(f"\n✓  Done. Total parishioners in DB: {total}")


if __name__ == "__main__":
    main()
