"""add label to mass schedules

Revision ID: j8e9f0a1b2c3
Revises: i7d8e9f0a1b2
Create Date: 2026-04-06

"""
from alembic import op
import sqlalchemy as sa

revision = 'j8e9f0a1b2c3'
down_revision = 'i7d8e9f0a1b2'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('mass_schedules', sa.Column('label', sa.String(100), nullable=True))


def downgrade():
    op.drop_column('mass_schedules', 'label')
