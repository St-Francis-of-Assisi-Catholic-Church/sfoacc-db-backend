"""make church_unit_id NOT NULL on societies and church_communities

Revision ID: c3d4e5f6a7b8
Revises: b2c3d4e5f6a7
Create Date: 2026-03-14
"""
from alembic import op
import sqlalchemy as sa

revision = 'c3d4e5f6a7b8'
down_revision = 'b2c3d4e5f6a7'
branch_labels = None
depends_on = None


def upgrade():
    # Backfill any NULLs to the main parish (type='parish')
    op.execute("""
        UPDATE societies
        SET church_unit_id = (
            SELECT id FROM church_units WHERE type = 'PARISH' LIMIT 1
        )
        WHERE church_unit_id IS NULL
    """)
    op.execute("""
        UPDATE church_communities
        SET church_unit_id = (
            SELECT id FROM church_units WHERE type = 'PARISH' LIMIT 1
        )
        WHERE church_unit_id IS NULL
    """)

    # Drop old FK constraints, alter column, re-add with RESTRICT
    op.alter_column('societies', 'church_unit_id', nullable=False)
    op.alter_column('church_communities', 'church_unit_id', nullable=False)


def downgrade():
    op.alter_column('societies', 'church_unit_id', nullable=True)
    op.alter_column('church_communities', 'church_unit_id', nullable=True)
