"""add is_active to societies and church_communities

Revision ID: b2c3d4e5f6a7
Revises: a1b2c3d4e5f6
Create Date: 2026-03-14
"""
from alembic import op
import sqlalchemy as sa

revision = 'b2c3d4e5f6a7'
down_revision = 'a1b2c3d4e5f6'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('societies', sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'))
    op.add_column('church_communities', sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'))


def downgrade():
    op.drop_column('societies', 'is_active')
    op.drop_column('church_communities', 'is_active')
