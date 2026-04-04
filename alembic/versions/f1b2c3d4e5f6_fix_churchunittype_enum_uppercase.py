"""fix_churchunittype_enum_uppercase

Revision ID: f1b2c3d4e5f6
Revises: e1a2b3c4d5e6
Create Date: 2026-03-14 00:00:00.000000

Converts the churchunittype PostgreSQL enum from lowercase labels
('parish', 'outstation') to uppercase labels ('PARISH', 'OUTSTATION')
to match SQLAlchemy's default behaviour of storing enum member *names*.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'f1b2c3d4e5f6'
down_revision: Union[str, None] = 'e1a2b3c4d5e6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Convert column to plain text so we can update the values freely.
    op.execute("ALTER TABLE church_units ALTER COLUMN type TYPE TEXT USING type::TEXT")

    # 2. Update existing lowercase rows to uppercase.
    op.execute("UPDATE church_units SET type = 'PARISH' WHERE type = 'parish'")
    op.execute("UPDATE church_units SET type = 'OUTSTATION' WHERE type = 'outstation'")

    # 3. Drop the old enum type (lowercase labels).
    op.execute("DROP TYPE IF EXISTS churchunittype")

    # 4. Create the new enum type with uppercase labels.
    op.execute("CREATE TYPE churchunittype AS ENUM ('PARISH', 'OUTSTATION')")

    # 5. Convert the column back to the new enum type.
    op.execute(
        "ALTER TABLE church_units ALTER COLUMN type TYPE churchunittype"
        " USING type::churchunittype"
    )


def downgrade() -> None:
    # 1. Convert column to plain text.
    op.execute("ALTER TABLE church_units ALTER COLUMN type TYPE TEXT USING type::TEXT")

    # 2. Revert uppercase rows to lowercase.
    op.execute("UPDATE church_units SET type = 'parish' WHERE type = 'PARISH'")
    op.execute("UPDATE church_units SET type = 'outstation' WHERE type = 'OUTSTATION'")

    # 3. Drop the uppercase enum type.
    op.execute("DROP TYPE IF EXISTS churchunittype")

    # 4. Recreate the old enum type with lowercase labels.
    op.execute("CREATE TYPE churchunittype AS ENUM ('parish', 'outstation')")

    # 5. Convert the column back to the old enum type.
    op.execute(
        "ALTER TABLE church_units ALTER COLUMN type TYPE churchunittype"
        " USING type::churchunittype"
    )
