"""add church_unit_leadership and church_events tables

Revision ID: d1e2f3a4b5c6
Revises: f1b2c3d4e5f6
Create Date: 2026-03-15 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = 'd1e2f3a4b5c6'
down_revision: Union[str, None] = 'c3d4e5f6a7b8'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    leadership_role_enum = postgresql.ENUM(
        'priest_in_charge', 'assistant_priest', 'deacon',
        'church_administrator', 'church_secretary',
        'ppc_chairman', 'ppc_vice_chairman', 'ppc_secretary', 'ppc_treasurer', 'ppc_member',
        'other',
        name='leadershiprole',
    )
    leadership_role_enum.create(op.get_bind(), checkfirst=True)

    op.create_table(
        'church_unit_leadership',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('church_unit_id', sa.Integer(), nullable=False),
        sa.Column('role', postgresql.ENUM(
            'priest_in_charge', 'assistant_priest', 'deacon',
            'church_administrator', 'church_secretary',
            'ppc_chairman', 'ppc_vice_chairman', 'ppc_secretary', 'ppc_treasurer', 'ppc_member',
            'other',
            name='leadershiprole', create_type=False,
        ), nullable=False),
        sa.Column('custom_role', sa.String(length=200), nullable=True),
        sa.Column('name', sa.String(length=200), nullable=False),
        sa.Column('phone', sa.String(length=50), nullable=True),
        sa.Column('email', sa.String(length=200), nullable=True),
        sa.Column('is_current', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('start_date', sa.Date(), nullable=True),
        sa.Column('end_date', sa.Date(), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.ForeignKeyConstraint(['church_unit_id'], ['church_units.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_church_unit_leadership_id', 'church_unit_leadership', ['id'])
    op.create_index('ix_church_unit_leadership_church_unit_id', 'church_unit_leadership', ['church_unit_id'])
    op.create_index('ix_church_unit_leadership_is_current', 'church_unit_leadership', ['is_current'])

    op.create_table(
        'church_events',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('church_unit_id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=300), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('event_date', sa.Date(), nullable=False),
        sa.Column('start_time', sa.Time(), nullable=True),
        sa.Column('end_time', sa.Time(), nullable=True),
        sa.Column('location', sa.String(length=500), nullable=True),
        sa.Column('is_public', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.ForeignKeyConstraint(['church_unit_id'], ['church_units.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_church_events_id', 'church_events', ['id'])
    op.create_index('ix_church_events_church_unit_id', 'church_events', ['church_unit_id'])
    op.create_index('ix_church_events_event_date', 'church_events', ['event_date'])


def downgrade() -> None:
    op.drop_index('ix_church_events_event_date', table_name='church_events')
    op.drop_index('ix_church_events_church_unit_id', table_name='church_events')
    op.drop_index('ix_church_events_id', table_name='church_events')
    op.drop_table('church_events')

    op.drop_index('ix_church_unit_leadership_is_current', table_name='church_unit_leadership')
    op.drop_index('ix_church_unit_leadership_church_unit_id', table_name='church_unit_leadership')
    op.drop_index('ix_church_unit_leadership_id', table_name='church_unit_leadership')
    op.drop_table('church_unit_leadership')

    op.execute("DROP TYPE IF EXISTS leadershiprole")
