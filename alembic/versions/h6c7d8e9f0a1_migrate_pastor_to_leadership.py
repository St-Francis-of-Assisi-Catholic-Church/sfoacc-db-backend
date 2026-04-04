"""migrate pastor fields to leadership table

Revision ID: h6c7d8e9f0a1
Revises: g5b6c7d8e9f0
Create Date: 2026-03-21

"""
from alembic import op
import sqlalchemy as sa

revision = 'h6c7d8e9f0a1'
down_revision = 'g5b6c7d8e9f0'
branch_labels = None
depends_on = None


def upgrade():
    # Migrate existing pastor data into church_unit_leadership
    op.execute("""
        INSERT INTO church_unit_leadership (church_unit_id, role, name, email, phone, is_current, created_at, updated_at)
        SELECT id, 'priest_in_charge', pastor_name, pastor_email, pastor_phone, true, now(), now()
        FROM church_units
        WHERE pastor_name IS NOT NULL AND pastor_name <> ''
    """)

    # Drop the pastor columns from church_units
    op.drop_column('church_units', 'pastor_name')
    op.drop_column('church_units', 'pastor_email')
    op.drop_column('church_units', 'pastor_phone')


def downgrade():
    op.add_column('church_units', sa.Column('pastor_name', sa.String(200), nullable=True))
    op.add_column('church_units', sa.Column('pastor_email', sa.String(200), nullable=True))
    op.add_column('church_units', sa.Column('pastor_phone', sa.String(50), nullable=True))
