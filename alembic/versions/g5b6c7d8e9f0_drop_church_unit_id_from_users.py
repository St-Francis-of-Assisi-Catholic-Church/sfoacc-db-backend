"""drop church_unit_id from users

Revision ID: g5b6c7d8e9f0
Revises: f4a5b6c7d8e9
Create Date: 2026-03-20
"""

from alembic import op
import sqlalchemy as sa

revision = "g5b6c7d8e9f0"
down_revision = "f4a5b6c7d8e9"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.drop_column("users", "church_unit_id")


def downgrade() -> None:
    op.add_column(
        "users",
        sa.Column(
            "church_unit_id",
            sa.Integer(),
            sa.ForeignKey("church_units.id", ondelete="SET NULL"),
            nullable=True,
        ),
    )
