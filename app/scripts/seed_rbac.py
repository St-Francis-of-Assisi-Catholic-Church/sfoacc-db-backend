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
    # Parishioners
    {"code": "parishioner:read",        "name": "View Parishioners",                "module": "parishioners"},
    {"code": "parishioner:write",       "name": "Create/Edit Parishioners",         "module": "parishioners"},
    {"code": "parishioner:delete",      "name": "Delete Parishioners",              "module": "parishioners"},
    {"code": "parishioner:import",      "name": "Import Parishioners (CSV)",        "module": "parishioners"},
    {"code": "parishioner:generate_id", "name": "Generate Church IDs",              "module": "parishioners"},
    {"code": "parishioner:verify",      "name": "Verify Parishioner Records",       "module": "parishioners"},
    # Societies
    {"code": "society:read",            "name": "View Societies",                   "module": "societies"},
    {"code": "society:write",           "name": "Manage Societies",                 "module": "societies"},
    {"code": "society:membership",      "name": "Manage Society Membership",        "module": "societies"},
    # Users
    {"code": "user:read",               "name": "View Users",                       "module": "users"},
    {"code": "user:write",              "name": "Create/Edit Users",                "module": "users"},
    {"code": "user:delete",             "name": "Delete Users",                     "module": "users"},
    # Admin – system / parish level
    {"code": "admin:all",               "name": "Full System Admin Access",         "module": "admin"},
    {"code": "admin:parish",            "name": "Manage Parish Info",               "module": "admin"},
    {"code": "admin:outstations",       "name": "Manage All Outstations",           "module": "admin"},
    {"code": "admin:settings",          "name": "Manage Parish Settings",           "module": "admin"},
    {"code": "admin:roles",             "name": "Manage Roles & Permissions",       "module": "admin"},
    # Admin – outstation level (scoped to user's own outstation)
    {"code": "admin:outstation",        "name": "Manage Own Outstation",            "module": "admin"},
    # Statistics / reporting
    {"code": "statistics:read",         "name": "View Statistics",                  "module": "statistics"},
    {"code": "reporting:read",          "name": "View Reports & Exports",           "module": "reporting"},
    # Messaging
    {"code": "messaging:send",          "name": "Send Bulk Messages",               "module": "messaging"},
    # Finance
    {"code": "finance:read",            "name": "View Financial Records",           "module": "finance"},
    {"code": "finance:write",           "name": "Manage Financial Records",         "module": "finance"},
    # Auth config (super admin only)
    {"code": "admin:auth_config",       "name": "Configure Login Methods",          "module": "admin"},
]

DEFAULT_ROLES = [
    {
        "name": "super_admin",
        "label": "Super Admin",
        "description": "Full access to everything across the entire system. Not scoped to any church unit.",
        "is_system": True,
        "permissions": ["admin:all"],
    },
    {
        "name": "church_administrator",
        "label": "Church Administrator",
        "description": (
            "Manages all operations for their assigned church unit — parishioners, societies, "
            "users, mass schedules, and settings. Scoped to one unit."
        ),
        "is_system": True,
        "permissions": [
            "parishioner:read", "parishioner:write", "parishioner:delete",
            "parishioner:import", "parishioner:generate_id", "parishioner:verify",
            "society:read", "society:write", "society:membership",
            "user:read", "user:write",
            "admin:outstation", "admin:settings",
            "statistics:read", "messaging:send",
        ],
    },
    {
        "name": "church_secretary",
        "label": "Church Secretary",
        "description": (
            "Handles parishioner records, church ID generation, and correspondence "
            "for their assigned church unit."
        ),
        "is_system": True,
        "permissions": [
            "parishioner:read", "parishioner:write", "parishioner:import",
            "parishioner:generate_id", "parishioner:verify",
            "society:read", "society:membership",
            "statistics:read", "messaging:send",
        ],
    },
    {
        "name": "church_finance_admin",
        "label": "Church Finance Admin",
        "description": (
            "Manages financial records and reports for their assigned church unit. "
            "Read-only access to parishioner data."
        ),
        "is_system": True,
        "permissions": [
            "finance:read", "finance:write",
            "statistics:read", "reporting:read",
            "parishioner:read",
        ],
    },
    {
        "name": "database_management_team",
        "label": "Database Management Team",
        "description": (
            "Handles data entry and parishioner record management for their assigned church unit. "
            "Can create and edit parishioner records, import from CSV, and manage society membership."
        ),
        "is_system": True,
        "permissions": [
            "parishioner:read", "parishioner:write", "parishioner:import",
            "society:read", "society:membership",
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
