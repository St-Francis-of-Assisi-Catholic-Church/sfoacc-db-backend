from typing import Any

from fastapi import APIRouter

from app.api.deps import SessionDep, CurrentUser, require_permission
from app.models.sacrament import Sacrament
from app.models.language import Language
from app.models.society import Society
from app.models.parish import ChurchUnit
from app.models.church_community import ChurchCommunity
from app.models.parishioner import Skill
from app.schemas.common import APIResponse

registration_schema_router = APIRouter()


def _field(key: str, label: str, field_type: str, required: bool = False, **kwargs) -> dict:
    return {"key": key, "label": label, "type": field_type, "required": required, **kwargs}


def _option(value: Any, label: str, **kwargs) -> dict:
    return {"value": value, "label": label, **kwargs}


GENDER_OPTIONS = [
    _option("male", "Male"),
    _option("female", "Female"),
    _option("other", "Other"),
]

MARITAL_STATUS_OPTIONS = [
    _option("single", "Single"),
    _option("married", "Married"),
    _option("widowed", "Widowed"),
    _option("divorced", "Divorced"),
    _option("separated", "Separated"),
]

LIFE_STATUS_OPTIONS = [
    _option("alive", "Alive"),
    _option("deceased", "Deceased"),
    _option("unknown", "Unknown"),
]

MEMBERSHIP_STATUS_OPTIONS = [
    _option("active", "Active"),
    _option("deceased", "Deceased"),
    _option("disabled", "Disabled"),
]


@registration_schema_router.get(
    "",
    response_model=APIResponse,
    dependencies=[require_permission("parishioner:write")],
    summary="Get parishioner registration form schema",
    description=(
        "Returns the full form schema for registering a parishioner, including field "
        "definitions, validation constraints, allowed values, and dynamic options fetched "
        "from the database (sacraments, languages, societies, church units, communities, skills). "
        "Use this to auto-build the registration form on the client side."
    ),
)
async def get_registration_schema(
    session: SessionDep,
    current_user: CurrentUser,
) -> Any:
    # --- Dynamic options from DB ---
    church_units = session.query(ChurchUnit).filter(ChurchUnit.is_active == True).order_by(ChurchUnit.name).all()
    church_unit_options = [
        _option(u.id, u.name, unit_type=u.type.value if hasattr(u.type, "value") else u.type)
        for u in church_units
    ]

    communities = (
        session.query(ChurchCommunity)
        .filter(ChurchCommunity.is_active == True)
        .order_by(ChurchCommunity.name)
        .all()
    )
    community_options = [_option(c.id, c.name) for c in communities]

    sacraments = session.query(Sacrament).order_by(Sacrament.id).all()
    sacrament_options = [
        _option(s.id, s.name, description=s.description, once_only=s.once_only)
        for s in sacraments
    ]

    languages = session.query(Language).order_by(Language.name).all()
    language_options = [_option(l.id, l.name) for l in languages]

    societies = (
        session.query(Society)
        .filter(Society.is_active == True)
        .order_by(Society.name)
        .all()
    )
    society_options = [_option(s.id, s.name, description=s.description) for s in societies]

    skills = session.query(Skill).order_by(Skill.name).all()
    existing_skill_options = [_option(s.id, s.name) for s in skills]

    # --- Schema sections ---
    schema = {
        "sections": [
            {
                "key": "personal_info",
                "label": "Personal Information",
                "type": "fields",
                "fields": [
                    _field("title", "Title", "text", max_length=20, placeholder="e.g. Mr, Mrs, Dr, Rev, Fr"),
                    _field("first_name", "First Name", "text", required=True, min_length=2, max_length=50),
                    _field("last_name", "Last Name (Surname)", "text", required=True, min_length=2, max_length=50),
                    _field("other_names", "Other Names", "text", max_length=100),
                    _field("maiden_name", "Maiden Name", "text", max_length=50),
                    _field("baptismal_name", "Baptismal / Christian Name", "text", max_length=100),
                    _field("gender", "Gender", "select", required=True, options=GENDER_OPTIONS),
                    _field("date_of_birth", "Date of Birth", "date"),
                    _field("place_of_birth", "Place of Birth", "text"),
                    _field("nationality", "Nationality", "text", max_length=100),
                    _field("hometown", "Hometown", "text"),
                    _field("region", "Region / State", "text"),
                    _field("country", "Country", "text"),
                    _field(
                        "marital_status", "Marital Status", "select",
                        default="single", options=MARITAL_STATUS_OPTIONS,
                    ),
                    _field("photo_url", "Photo URL", "url", max_length=500),
                    _field("notes", "Notes / Additional Info", "textarea"),
                ],
            },
            {
                "key": "contact_info",
                "label": "Contact Information",
                "type": "fields",
                "fields": [
                    _field("mobile_number", "Mobile Number", "tel"),
                    _field("whatsapp_number", "WhatsApp Number", "tel"),
                    _field("email_address", "Email Address", "email"),
                    _field("current_residence", "Current Residence / Address", "text"),
                ],
            },
            {
                "key": "church_placement",
                "label": "Church Placement",
                "type": "fields",
                "description": "Assign the parishioner to a church unit and/or community.",
                "fields": [
                    _field("church_unit_id", "Church Unit / Outstation", "select", options=church_unit_options),
                    _field("church_community_id", "Church Community", "select", options=community_options),
                    _field("old_church_id", "Old Church ID", "text"),
                ],
            },
            {
                "key": "status",
                "label": "Membership & Vital Status",
                "type": "fields",
                "fields": [
                    _field(
                        "membership_status", "Membership Status", "select",
                        default="active", options=MEMBERSHIP_STATUS_OPTIONS,
                    ),
                    _field("is_deceased", "Is Deceased", "boolean", default=False),
                    _field(
                        "date_of_death", "Date of Death", "date",
                        conditional={"field": "is_deceased", "value": True},
                    ),
                ],
            },
            {
                "key": "occupation",
                "label": "Occupation",
                "type": "object",
                "description": "Employment / occupation details. Omit this section entirely if not applicable.",
                "fields": [
                    _field("role", "Job Title / Role", "text", required=True),
                    _field("employer", "Employer / Organization", "text", required=True),
                ],
            },
            {
                "key": "family_info",
                "label": "Family Information",
                "type": "object",
                "description": "Spouse, parents, and children.",
                "fields": [
                    _field("spouse_name", "Spouse's Name", "text", max_length=100),
                    _field("spouse_status", "Spouse's Status", "select", options=LIFE_STATUS_OPTIONS),
                    _field("spouse_phone", "Spouse's Phone", "tel", max_length=20),
                    _field("father_name", "Father's Name", "text", max_length=100),
                    _field("father_status", "Father's Status", "select", options=LIFE_STATUS_OPTIONS),
                    _field("mother_name", "Mother's Name", "text", max_length=100),
                    _field("mother_status", "Mother's Status", "select", options=LIFE_STATUS_OPTIONS),
                    {
                        "key": "children",
                        "label": "Children",
                        "type": "repeatable_section",
                        "required": False,
                        "fields": [
                            _field("name", "Child's Name", "text", required=True, min_length=2, max_length=100),
                        ],
                    },
                ],
            },
            {
                "key": "emergency_contacts",
                "label": "Emergency Contacts",
                "type": "repeatable_section",
                "description": "Up to 3 emergency contacts.",
                "max_items": 3,
                "fields": [
                    _field("name", "Contact Name", "text", required=True),
                    _field("relationship", "Relationship", "text", required=True, placeholder="e.g. Spouse, Sibling, Friend"),
                    _field("primary_phone", "Primary Phone", "tel", required=True),
                    _field("alternative_phone", "Alternative Phone", "tel"),
                ],
            },
            {
                "key": "medical_conditions",
                "label": "Medical Conditions",
                "type": "repeatable_section",
                "description": "Up to 5 known medical conditions.",
                "max_items": 5,
                "fields": [
                    _field("condition", "Condition", "text", required=True),
                    _field("notes", "Notes", "textarea"),
                ],
            },
            {
                "key": "sacraments",
                "label": "Sacraments",
                "type": "repeatable_section",
                "description": (
                    "Sacraments received by the parishioner. "
                    "Sacraments marked once_only can only be recorded once per parishioner."
                ),
                "fields": [
                    _field("sacrament_id", "Sacrament", "select", required=True, options=sacrament_options),
                    _field("date_received", "Date Received", "date"),
                    _field("place", "Place / Church", "text"),
                    _field("minister", "Officiating Minister", "text"),
                    _field("notes", "Notes", "textarea"),
                ],
            },
            {
                "key": "skills",
                "label": "Skills & Talents",
                "type": "tag_input",
                "description": (
                    "Skills and talents of the parishioner. "
                    "You may select from existing skills or add new ones by name."
                ),
                "field": _field("name", "Skill Name", "text", required=True),
                "existing_options": existing_skill_options,
            },
            {
                "key": "languages",
                "label": "Languages Spoken",
                "type": "multiselect",
                "description": "Languages spoken by the parishioner.",
                "options": language_options,
                "submit_as": "language_ids",
            },
            {
                "key": "societies",
                "label": "Society Memberships",
                "type": "repeatable_section",
                "description": "Societies the parishioner belongs to.",
                "fields": [
                    _field("society_id", "Society", "select", required=True, options=society_options),
                    _field("date_joined", "Date Joined", "date"),
                ],
            },
        ]
    }

    return APIResponse(message="Registration schema retrieved successfully", data=schema)
