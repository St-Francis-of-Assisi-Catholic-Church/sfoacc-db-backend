"""add tokens_invalidated_before to users

Revision ID: k9f0a1b2c3d4
Revises: j8e9f0a1b2c3
Create Date: 2026-04-06

"""
from alembic import op
import sqlalchemy as sa

revision = 'k9f0a1b2c3d4'
down_revision = 'j8e9f0a1b2c3'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('users', sa.Column('tokens_invalidated_before', sa.DateTime(timezone=True), nullable=True))


def downgrade():
    op.drop_column('users', 'tokens_invalidated_before')
