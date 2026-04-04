"""add audit_logs table

Revision ID: a1b2c3d4e5f6
Revises: f1b2c3d4e5f6
Create Date: 2026-03-15
"""
from alembic import op
import sqlalchemy as sa
import sqlalchemy.dialects.postgresql

revision = 'a1b2c3d4e5f6'
down_revision = 'c2d3e4f5a6b7'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'audit_logs',
        sa.Column('id', sa.Integer(), primary_key=True, index=True),
        sa.Column('user_id', sa.dialects.postgresql.UUID(as_uuid=False), sa.ForeignKey('users.id', ondelete='SET NULL'), nullable=True, index=True),
        sa.Column('method', sa.String(10), nullable=False),
        sa.Column('path', sa.String(500), nullable=False),
        sa.Column('status_code', sa.Integer(), nullable=True),
        sa.Column('ip_address', sa.String(45), nullable=True),
        sa.Column('user_agent', sa.String(500), nullable=True),
        sa.Column('summary', sa.String(500), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now(), index=True),
    )


def downgrade():
    op.drop_table('audit_logs')
