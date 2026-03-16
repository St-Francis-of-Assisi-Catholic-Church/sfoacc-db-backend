#!/usr/bin/env python3
"""
Generate sdk/types.ts from the FastAPI OpenAPI schema.

Run directly:
    python3 -m scripts.gen_sdk
Or via Make:
    make sdk
"""

from __future__ import annotations

import os
import sys
import textwrap
from typing import Any

# Make sure the app root is importable
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from app.main import app  # noqa: E402 — needs sys.path set first

# ── TypeScript preamble (utility types not in OpenAPI schema) ─────────────────

PREAMBLE = textwrap.dedent("""\
    // AUTO-GENERATED — do not edit by hand.
    // Regenerate with: make sdk
    //
    // Generated from FastAPI OpenAPI schema via scripts/gen_sdk.py

    // ── Response wrappers ──────────────────────────────────────────────────────

    export interface APIResponse<T = unknown> {
      message: string;
      data: T | null;
    }

    /** Standard paginated payload — always lives inside APIResponse.data */
    export interface PagedData<T> {
      items: T[];
      total: number;
      skip: number;
      limit: number;
    }

    export type PagedResponse<T> = APIResponse<PagedData<T>>;

""")

# ── Schemas we want to skip (internal FastAPI plumbing) ──────────────────────
SKIP_SCHEMAS = {
    "HTTPValidationError",
    "ValidationError",
    "ValidationErrorLocItem",
}

# ── Override generated names → TypeScript type alias declarations ─────────────
# Use this to emit `export type Foo = Bar;` when openapi schema name differs
# from what client.ts / hooks.ts imports.
ALIASES: dict[str, str] = {
    # These enums get long module-path names from FastAPI disambiguation.
    # Provide clean aliases for use in client.ts / hooks.ts.
    "LeadershipRole": "AppModelsChurchUnitAdminLeadershiprole",
    "SocietyLeadershipRole": "AppModelsSocietyLeadershiprole",
}

# ── Helpers ───────────────────────────────────────────────────────────────────

def _to_camel_case(name: str) -> str:
    """
    Convert an OpenAPI schema name to a valid PascalCase TypeScript identifier.
    e.g. 'Body_authentication-login' → 'BodyAuthenticationLogin'
         'ChurchUnitCreate'          → 'ChurchUnitCreate'  (no separators → preserve)
         'my_schema-name'            → 'MySchemaName'
    """
    import re
    # If the name has no separators it is already a valid Python/Pydantic class
    # name (PascalCase). Preserve it exactly rather than lowercasing everything.
    if not re.search(r"[_\-]", name):
        return name
    # Split on underscores and hyphens, capitalise each part
    parts = re.split(r"[_\-]+", name)
    return "".join(p.capitalize() for p in parts if p)


def _resolve_ref(ref: str) -> str:
    """'#/components/schemas/Foo' → camelCase TS name"""
    raw = ref.split("/")[-1]
    return _to_camel_case(raw)


def _to_ts_type(schema: dict[str, Any], all_schemas: dict[str, Any], depth: int = 0) -> str:
    """Recursively convert a JSON Schema node to a TypeScript type string."""
    if not schema:
        return "unknown"

    # $ref
    if "$ref" in schema:
        return _resolve_ref(schema["$ref"])

    # anyOf / oneOf → union (commonly used for Optional[X] → anyOf: [X, null])
    for key in ("anyOf", "oneOf"):
        if key in schema:
            parts = [_to_ts_type(s, all_schemas, depth) for s in schema[key]]
            non_null = [p for p in parts if p != "null"]
            is_nullable = len(non_null) < len(parts)
            base = " | ".join(non_null) if non_null else "unknown"
            return f"{base} | null" if is_nullable else base

    # allOf with a single ref is just an alias
    if "allOf" in schema:
        if len(schema["allOf"]) == 1:
            return _to_ts_type(schema["allOf"][0], all_schemas, depth)
        # multiple allOf → intersection
        parts = [_to_ts_type(s, all_schemas, depth) for s in schema["allOf"]]
        return " & ".join(parts)

    t = schema.get("type")

    if t == "string":
        if "enum" in schema:
            return " | ".join(f'"{v}"' for v in schema["enum"])
        return "string"

    if t in ("integer", "number"):
        return "number"

    if t == "boolean":
        return "boolean"

    if t == "null":
        return "null"

    if t == "array":
        items = schema.get("items", {})
        return f"{_to_ts_type(items, all_schemas, depth)}[]"

    if t == "object" or "properties" in schema:
        props = schema.get("properties", {})
        if not props:
            return "Record<string, unknown>"
        indent = "  " * (depth + 1)
        lines = ["{"]
        required = set(schema.get("required", []))
        for prop_name, prop_schema in props.items():
            ts_t = _to_ts_type(prop_schema, all_schemas, depth + 1)
            opt = "" if prop_name in required else "?"
            lines.append(f"{indent}{prop_name}{opt}: {ts_t};")
        lines.append("  " * depth + "}")
        return "\n".join(lines)

    return "unknown"


def _emit_schema(name: str, schema_def: dict[str, Any], all_schemas: dict[str, Any]) -> str:
    """Return the TypeScript declaration(s) for a single OpenAPI schema."""
    lines: list[str] = []

    # ── Pure enum ─────────────────────────────────────────────────────────────
    if "enum" in schema_def and schema_def.get("type") == "string":
        vals = " | ".join(f'"{v}"' for v in schema_def["enum"])
        lines.append(f"export type {name} = {vals};\n")
        return "\n".join(lines)

    # ── allOf: inheritance / composition ──────────────────────────────────────
    if "allOf" in schema_def and not schema_def.get("properties"):
        refs = [s["$ref"].split("/")[-1] for s in schema_def["allOf"] if "$ref" in s]
        extra: dict[str, Any] = {}
        for s in schema_def["allOf"]:
            extra.update(s.get("properties", {}))
        # Gather required from all allOf entries
        required: set[str] = set(schema_def.get("required", []))
        for s in schema_def["allOf"]:
            required.update(s.get("required", []))

        if refs and not extra:
            lines.append(f"export type {name} = {refs[0]};\n")
            return "\n".join(lines)

        extends_clause = f" extends {', '.join(refs)}" if refs else ""
        lines.append(f"export interface {name}{extends_clause} {{")
        for prop_name, prop_schema in extra.items():
            ts_t = _to_ts_type(prop_schema, all_schemas)
            opt = "" if prop_name in required else "?"
            lines.append(f"  {prop_name}{opt}: {ts_t};")
        lines.append("}\n")
        return "\n".join(lines)

    # ── Standard object ───────────────────────────────────────────────────────
    if schema_def.get("type") == "object" or "properties" in schema_def:
        props = schema_def.get("properties", {})
        required = set(schema_def.get("required", []))
        lines.append(f"export interface {name} {{")
        for prop_name, prop_schema in props.items():
            ts_t = _to_ts_type(prop_schema, all_schemas)
            opt = "" if prop_name in required else "?"
            lines.append(f"  {prop_name}{opt}: {ts_t};")
        lines.append("}\n")
        return "\n".join(lines)

    # ── Fallback: type alias ──────────────────────────────────────────────────
    ts_t = _to_ts_type(schema_def, all_schemas)
    lines.append(f"export type {name} = {ts_t};\n")
    return "\n".join(lines)


# ── Main ──────────────────────────────────────────────────────────────────────

def main() -> None:
    openapi_schema = app.openapi()
    all_schemas: dict[str, Any] = (
        openapi_schema.get("components", {}).get("schemas", {})
    )

    output = [PREAMBLE, "// ── Generated schema types ───────────────────────────────────────────────────\n"]

    emitted = 0
    skipped = 0

    for schema_name in sorted(all_schemas.keys()):
        if schema_name in SKIP_SCHEMAS:
            skipped += 1
            continue
        ts_name = _to_camel_case(schema_name)
        schema_def = all_schemas[schema_name]
        output.append(_emit_schema(ts_name, schema_def, all_schemas))
        emitted += 1

    # Emit any explicit aliases
    if ALIASES:
        output.append("\n// ── Aliases ──────────────────────────────────────────────────────────────────\n")
        for alias, target in sorted(ALIASES.items()):
            output.append(f"export type {alias} = {target};\n")

    # Pagination helpers not in OpenAPI schema
    output.append(textwrap.dedent("""\

        // ── Pagination helpers ────────────────────────────────────────────────────────

        export interface PaginationParams {
          skip?: number;
          limit?: number;
        }
    """))

    # Response / read types — not in OpenAPI schema (routes use untyped APIResponse).
    # These must come after the generated enums they reference.
    output.append(textwrap.dedent("""\

        // ── Response / read types ─────────────────────────────────────────────────────

        export interface MassSchedule {
          id: number;
          church_unit_id: number;
          day_of_week: DayOfWeek;
          time: string;
          mass_type: MassType;
          language: string;
          description?: string | null;
          is_active: boolean;
          created_at: string;
          updated_at: string;
        }

        export interface ChurchUnit {
          id: number;
          type: ChurchUnitType;
          parent_id?: number | null;
          name: string;
          diocese?: string | null;
          address?: string | null;
          phone?: string | null;
          email?: string | null;
          website?: string | null;
          established_date?: string | null;
          pastor_name?: string | null;
          pastor_email?: string | null;
          pastor_phone?: string | null;
          location_description?: string | null;
          google_maps_url?: string | null;
          latitude?: number | null;
          longitude?: number | null;
          priest_in_charge?: string | null;
          priest_phone?: string | null;
          is_active: boolean;
          created_at: string;
          updated_at: string;
        }

        export interface SocietySummary {
          id: number;
          name: string;
          description?: string | null;
          meeting_day?: string | null;
          meeting_time?: string | null;
          meeting_venue?: string | null;
        }

        export interface CommunitySummary {
          id: number;
          name: string;
          description?: string | null;
          location?: string | null;
        }

        export interface OutstationDetail extends ChurchUnit {
          mass_schedules: MassSchedule[];
          societies: SocietySummary[];
          communities: CommunitySummary[];
        }

        export interface ParishDetail extends ChurchUnit {
          mass_schedules: MassSchedule[];
          societies: SocietySummary[];
          communities: CommunitySummary[];
          outstations: OutstationDetail[];
        }

        export interface LeadershipRead {
          id: number;
          church_unit_id: number;
          role: LeadershipRole;
          custom_role?: string | null;
          name: string;
          phone?: string | null;
          email?: string | null;
          is_current: boolean;
          start_date?: string | null;
          end_date?: string | null;
          notes?: string | null;
          created_at: string;
          updated_at: string;
        }

        export interface ChurchEventRead {
          id: number;
          church_unit_id: number;
          name: string;
          description?: string | null;
          event_date: string;
          start_time?: string | null;
          end_time?: string | null;
          location?: string | null;
          is_public: boolean;
          created_at: string;
          updated_at: string;
        }

        export interface SocietyLeadershipRead {
          id: number;
          role: SocietyLeadershipRole;
          custom_role?: string | null;
          elected_date?: string | null;
          end_date?: string | null;
          parishioner_id: string;
          parishioner_name: string;
          parishioner_church_id?: string | null;
          parishioner_contact?: string | null;
        }

        export interface Society {
          id: number;
          name: string;
          description?: string | null;
          date_inaugurated?: string | null;
          is_active: boolean;
          church_unit_id?: number | null;
          church_unit_name?: string | null;
          meeting_frequency: MeetingFrequency;
          meeting_day?: string | null;
          meeting_time?: string | null;
          meeting_venue?: string | null;
          members_count: number;
          leadership: SocietyLeadershipRead[];
          created_at: string;
          updated_at: string;
        }

        export interface SocietyMember {
          parishioner_id: string;
          first_name: string;
          last_name: string;
          other_names?: string | null;
          mobile_number?: string | null;
          date_joined?: string | null;
          membership_status?: string | null;
        }

        export interface ChurchCommunity {
          id: number;
          name: string;
          description?: string | null;
          location?: string | null;
          is_active: boolean;
          church_unit_id: number;
          created_at: string;
          updated_at: string;
        }

        export interface Parishioner {
          id: string;
          title?: string | null;
          old_church_id?: string | null;
          new_church_id?: string | null;
          first_name: string;
          other_names?: string | null;
          last_name: string;
          maiden_name?: string | null;
          baptismal_name?: string | null;
          gender: Gender;
          date_of_birth?: string | null;
          place_of_birth?: string | null;
          nationality?: string | null;
          hometown?: string | null;
          region?: string | null;
          country?: string | null;
          marital_status?: MaritalStatus | null;
          mobile_number?: string | null;
          whatsapp_number?: string | null;
          email_address?: string | null;
          current_residence?: string | null;
          is_deceased: boolean;
          date_of_death?: string | null;
          photo_url?: string | null;
          notes?: string | null;
          church_community_id?: number | null;
          church_unit_id?: number | null;
          membership_status?: MembershipStatus | null;
          verification_status?: VerificationStatus | null;
          created_at: string;
          updated_at: string;
        }

        export interface ScheduledMessageRead {
          id: number;
          channel: string;
          template: string;
          custom_message?: string | null;
          subject?: string | null;
          event_name?: string | null;
          event_date?: string | null;
          event_time?: string | null;
          send_at: string;
          status: "pending" | "processing" | "sent" | "failed" | "cancelled";
          sent_count: number;
          error_message?: string | null;
          recipient_count: number;
          created_at: string;
        }

        export interface ParishionerDetailed extends Parishioner {
          occupation?: { id: number; role: string; employer: string } | null;
          family?: {
            spouse_name?: string | null;
            spouse_status?: string | null;
            spouse_phone?: string | null;
            father_name?: string | null;
            father_status?: string | null;
            mother_name?: string | null;
            mother_status?: string | null;
            children?: Array<{ name: string }>;
          } | null;
          emergency_contacts: Array<{
            id: number;
            name: string;
            relationship: string;
            primary_phone: string;
            alternative_phone?: string | null;
          }>;
          medical_conditions: Array<{ id: number; condition: string; notes?: string | null }>;
          skills: Array<{ id: number; name: string }>;
          sacraments: Array<{
            id: number;
            sacrament: { id: number; type: string };
            date_received?: string | null;
            place?: string | null;
            minister?: string | null;
            notes?: string | null;
          }>;
          societies: Array<{ id: number; name: string; date_joined?: string | null }>;
        }

        export interface ParishionerFilters extends PaginationParams {
          search?: string;
          gender?: Gender;
          marital_status?: MaritalStatus;
          membership_status?: MembershipStatus;
          verification_status?: VerificationStatus;
          church_unit_id?: number;
          church_community_id?: number;
        }

        /** Alias — ParishionerUpdate and ParishionerPartialUpdate are the same shape. */
        export type ParishionerUpdate = ParishionerPartialUpdate;

        export interface PermissionRead {
          id: number;
          code: string;
          name: string;
          description?: string | null;
          module: string;
        }

        export interface RoleRead {
          id: number;
          name: string;
          label: string;
          description?: string | null;
          is_system: boolean;
          permissions: PermissionRead[];
          created_at: string;
          updated_at: string;
        }

        export interface SettingRead {
          id: number;
          key: string;
          value?: string | null;
          label?: string | null;
          description?: string | null;
          church_unit_id: number;
          created_at: string;
          updated_at: string;
        }
    """))

    result = "\n".join(output)

    out_path = os.path.join(ROOT, "sdk", "types.ts")
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    with open(out_path, "w") as f:
        f.write(result)

    print(f"✓  sdk/types.ts updated  ({emitted} types exported, {skipped} skipped)")


if __name__ == "__main__":
    main()
