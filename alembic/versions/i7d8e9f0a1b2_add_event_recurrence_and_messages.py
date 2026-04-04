"""add event recurrence fields and event_messages table

Revision ID: i7d8e9f0a1b2
Revises: h6c7d8e9f0a1
Create Date: 2026-03-22 00:00:00.000000
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = 'i7d8e9f0a1b2'
down_revision: Union[str, None] = 'h6c7d8e9f0a1'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ── New enum types ────────────────────────────────────────────────────────
    recurrence_freq_enum = postgresql.ENUM(
        'daily', 'weekly', 'monthly', 'yearly',
        name='recurrencefrequency',
    )
    recurrence_freq_enum.create(op.get_bind(), checkfirst=True)

    event_msg_type_enum = postgresql.ENUM(
        'reminder', 'announcement', 'note',
        name='eventmessagetype',
    )
    event_msg_type_enum.create(op.get_bind(), checkfirst=True)

    # ── Recurrence columns on church_events ───────────────────────────────────
    op.add_column('church_events', sa.Column('is_recurring', sa.Boolean(), nullable=False, server_default='false'))
    op.add_column('church_events', sa.Column(
        'recurrence_frequency',
        postgresql.ENUM('daily', 'weekly', 'monthly', 'yearly', name='recurrencefrequency', create_type=False),
        nullable=True,
    ))
    op.add_column('church_events', sa.Column('recurrence_day_of_week', sa.SmallInteger(), nullable=True))
    op.add_column('church_events', sa.Column('recurrence_end_date', sa.Date(), nullable=True))
    op.add_column('church_events', sa.Column('terminated_at', sa.DateTime(timezone=True), nullable=True))

    op.create_index('ix_church_events_is_recurring', 'church_events', ['is_recurring'])

    # ── event_messages table ──────────────────────────────────────────────────
    op.create_table(
        'event_messages',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('event_id', sa.Integer(), nullable=False),
        sa.Column(
            'message_type',
            postgresql.ENUM('reminder', 'announcement', 'note', name='eventmessagetype', create_type=False),
            nullable=False,
            server_default='note',
        ),
        sa.Column('title', sa.String(length=300), nullable=True),
        sa.Column('content', sa.Text(), nullable=False),
        sa.Column('scheduled_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('is_sent', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('created_by_id', sa.UUID(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.ForeignKeyConstraint(['event_id'], ['church_events.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['created_by_id'], ['users.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_event_messages_id', 'event_messages', ['id'])
    op.create_index('ix_event_messages_event_id', 'event_messages', ['event_id'])


def downgrade() -> None:
    op.drop_index('ix_event_messages_event_id', table_name='event_messages')
    op.drop_index('ix_event_messages_id', table_name='event_messages')
    op.drop_table('event_messages')

    op.drop_index('ix_church_events_is_recurring', table_name='church_events')
    op.drop_column('church_events', 'terminated_at')
    op.drop_column('church_events', 'recurrence_end_date')
    op.drop_column('church_events', 'recurrence_day_of_week')
    op.drop_column('church_events', 'recurrence_frequency')
    op.drop_column('church_events', 'is_recurring')

    op.execute("DROP TYPE IF EXISTS eventmessagetype")
    op.execute("DROP TYPE IF EXISTS recurrencefrequency")
