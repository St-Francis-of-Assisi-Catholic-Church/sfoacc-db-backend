"""
Seed default RBAC roles and permissions.
Run: python -m app.scripts.seed_rbac
"""
import logging
from app.core.database import db
from app.models.rbac import Role, Permission

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

PERMISSIONS = [
    # ── Parishioners ──────────────────────────────────────────────────────────
    {"code": "parishioner:read",        "name": "View Parishioners",                "module": "parishioners"},
    {"code": "parishioner:write",       "name": "Create/Edit Parishioners",         "module": "parishioners"},
    {"code": "parishioner:delete",      "name": "Delete Parishioners",              "module": "parishioners"},
    {"code": "parishioner:import",      "name": "Import Parishioners (CSV)",        "module": "parishioners"},
    {"code": "parishioner:generate_id", "name": "Generate Church IDs",              "module": "parishioners"},
    {"code": "parishioner:verify",      "name": "Send Verification Codes",          "module": "parishioners"},
    # ── Societies ─────────────────────────────────────────────────────────────
    {"code": "society:read",            "name": "View Societies",                   "module": "societies"},
    {"code": "society:write",           "name": "Create/Edit Societies",            "module": "societies"},
    {"code": "society:delete",          "name": "Delete Societies",                 "module": "societies"},
    {"code": "society:membership",      "name": "Manage Society Membership",        "module": "societies"},
    # ── Church Communities ────────────────────────────────────────────────────
    {"code": "community:read",          "name": "View Church Communities",          "module": "communities"},
    {"code": "community:write",         "name": "Create/Edit Church Communities",   "module": "communities"},
    {"code": "community:delete",        "name": "Delete Church Communities",        "module": "communities"},
    {"code": "community:membership",    "name": "Manage Community Membership",      "module": "communities"},
    # ── Church Units ──────────────────────────────────────────────────────────
    {"code": "church_unit:read",        "name": "View Church Units & Outstations",  "module": "church_units"},
    # ── App Users ─────────────────────────────────────────────────────────────
    {"code": "user:read",               "name": "View App Users",                   "module": "users"},
    {"code": "user:write",              "name": "Create/Edit App Users",            "module": "users"},
    {"code": "user:delete",             "name": "Delete App Users",                 "module": "users"},
    # ── Messaging ─────────────────────────────────────────────────────────────
    {"code": "messaging:read",          "name": "View Message History & Templates", "module": "messaging"},
    {"code": "messaging:send",          "name": "Send Bulk Messages",               "module": "messaging"},
    # ── Statistics & Reporting ────────────────────────────────────────────────
    {"code": "statistics:read",         "name": "View Statistics & Dashboards",     "module": "statistics"},
    {"code": "reporting:read",          "name": "View Reports & Exports",           "module": "reporting"},
    # ── Finance ───────────────────────────────────────────────────────────────
    {"code": "finance:read",            "name": "View Financial Records",           "module": "finance"},
    {"code": "finance:write",           "name": "Manage Financial Records",         "module": "finance"},
    # ── Admin – system / parish level ─────────────────────────────────────────
    {"code": "admin:all",               "name": "Full System Admin Access",         "module": "admin"},
    {"code": "admin:parish",            "name": "Manage Parish Info",               "module": "admin"},
    {"code": "admin:outstations",       "name": "Manage All Outstations",           "module": "admin"},
    {"code": "admin:outstation",        "name": "Manage Own Outstation",            "module": "admin"},
    {"code": "admin:settings",          "name": "Manage Parish Settings",           "module": "admin"},
    {"code": "admin:roles",             "name": "Manage Roles & Permissions",       "module": "admin"},
    {"code": "admin:auth_config",       "name": "Configure Login Methods",          "module": "admin"},
]

DEFAULT_ROLES = [
    # ── Super Admin ───────────────────────────────────────────────────────────
    # Full unrestricted access. The admin:all permission bypasses every other
    # permission check in the system.
    {
        "name": "super_admin",
        "label": "Super Admin",
        "description": (
            "Full unrestricted access across the entire system. "
            "Only super admins can manage system-level roles, settings, and auth config."
        ),
        "is_system": True,
        "permissions": ["admin:all"],
    },

    # ── Church Administrator ──────────────────────────────────────────────────
    # Full CRUD on all entities within their unit. Can add/edit unit users.
    # Cannot touch system roles, auth config, or other units.
    {
        "name": "church_administrator",
        "label": "Church Administrator",
        "description": (
            "Full CRUD on parishioners, societies, communities, and messaging within their "
            "assigned unit. Can add and edit users scoped to their unit. Cannot manage "
            "system settings or other units."
        ),
        "is_system": True,
        "permissions": [
            # Parishioners — full
            "parishioner:read", "parishioner:write", "parishioner:delete",
            "parishioner:import", "parishioner:generate_id", "parishioner:verify",
            # Societies — full
            "society:read", "society:write", "society:delete", "society:membership",
            # Communities — full
            "community:read", "community:write", "community:delete", "community:membership",
            # Church units — read only
            "church_unit:read",
            # App users — read + write (no delete)
            "user:read", "user:write",
            # Messaging — full
            "messaging:read", "messaging:send",
            # Statistics & reporting
            "statistics:read", "reporting:read",
            # Unit admin
            "admin:outstation", "admin:settings",
        ],
    },

    # ── Church Secretary ──────────────────────────────────────────────────────
    # Full CRUD on all church entities. Can only VIEW users, never create/edit.
    {
        "name": "church_secretary",
        "label": "Church Secretary",
        "description": (
            "Full CRUD on parishioners, societies, communities, messaging, and parish records. "
            "Read-only access to app users — cannot create or edit system accounts."
        ),
        "is_system": True,
        "permissions": [
            # Parishioners — full
            "parishioner:read", "parishioner:write", "parishioner:delete",
            "parishioner:import", "parishioner:generate_id", "parishioner:verify",
            # Societies — full
            "society:read", "society:write", "society:delete", "society:membership",
            # Communities — full
            "community:read", "community:write", "community:delete", "community:membership",
            # Church units — read only
            "church_unit:read",
            # App users — read only
            "user:read",
            # Messaging — full
            "messaging:read", "messaging:send",
            # Statistics & reporting
            "statistics:read", "reporting:read",
            # Unit admin
            "admin:parish", "admin:outstation",
        ],
    },

    # ── Database Management Team ──────────────────────────────────────────────
    # Data entry focus: parishioner records, ID generation, verification,
    # society memberships. Can READ church units (needed to assign parishioners).
    # No user management, no community write, no admin settings.
    {
        "name": "database_management_team",
        "label": "Database Management Team",
        "description": (
            "Data entry and parishioner record management. Can add/edit/import parishioner "
            "records, generate church IDs, send verifications, and manage society membership. "
            "Read-only access to church units and communities. No user or admin access."
        ),
        "is_system": True,
        "permissions": [
            # Parishioners — full except delete
            "parishioner:read", "parishioner:write", "parishioner:import",
            "parishioner:generate_id", "parishioner:verify",
            # Societies — read, write, membership (no delete)
            "society:read", "society:write", "society:membership",
            # Communities — read + membership only
            "community:read", "community:membership",
            # Church units — read only (needed to assign parishioners to units)
            "church_unit:read",
            # Messaging — send only
            "messaging:send",
            # Statistics — view only
            "statistics:read",
        ],
    },

    # ── Finance ───────────────────────────────────────────────────────────────
    # Read-only across the board. No write access anywhere.
    {
        "name": "church_finance_admin",
        "label": "Finance",
        "description": (
            "Read-only access to parishioner data, church unit info, financial records, "
            "reports, and statistics. Cannot create, edit, or delete any records."
        ),
        "is_system": True,
        "permissions": [
            "parishioner:read",
            "church_unit:read",
            "finance:read",
            "statistics:read",
            "reporting:read",
        ],
    },
]


def seed_rbac():
    db.init_app()
    with db.session() as session:
        # Upsert permissions
        perm_map = {}
        for p_data in PERMISSIONS:
            perm = session.query(Permission).filter(Permission.code == p_data["code"]).first()
            if not perm:
                perm = Permission(**p_data)
                session.add(perm)
                logger.info(f"Created permission: {p_data['code']}")
            else:
                perm.name = p_data["name"]
                perm.module = p_data["module"]
            perm_map[p_data["code"]] = perm
        session.flush()

        # Upsert roles
        for r_data in DEFAULT_ROLES:
            perm_codes = r_data.pop("permissions")
            role = session.query(Role).filter(Role.name == r_data["name"]).first()
            if not role:
                role = Role(**r_data)
                session.add(role)
                logger.info(f"Created role: {r_data['name']}")
            else:
                role.label = r_data["label"]
                role.description = r_data["description"]
                role.is_system = r_data["is_system"]
            role.permissions = [perm_map[code] for code in perm_codes if code in perm_map]

        logger.info("RBAC seeding complete.")


if __name__ == "__main__":
    seed_rbac()
