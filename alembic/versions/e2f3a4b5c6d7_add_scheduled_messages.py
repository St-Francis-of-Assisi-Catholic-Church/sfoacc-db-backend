"""add scheduled_messages table

Revision ID: e2f3a4b5c6d7
Revises: d1e2f3a4b5c6
Create Date: 2026-03-15 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = 'e2f3a4b5c6d7'
down_revision: Union[str, None] = 'd1e2f3a4b5c6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    scheduled_message_status_enum = postgresql.ENUM(
        'pending', 'processing', 'sent', 'failed', 'cancelled',
        name='scheduledmessagestatus',
    )
    scheduled_message_status_enum.create(op.get_bind(), checkfirst=True)

    op.create_table(
        'scheduled_messages',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('parishioner_ids', sa.JSON(), nullable=False),
        sa.Column('channel', sa.String(length=10), nullable=False),
        sa.Column('template', sa.String(length=100), nullable=False),
        sa.Column('custom_message', sa.Text(), nullable=True),
        sa.Column('subject', sa.String(length=300), nullable=True),
        sa.Column('event_name', sa.String(length=200), nullable=True),
        sa.Column('event_date', sa.String(length=50), nullable=True),
        sa.Column('event_time', sa.String(length=50), nullable=True),
        sa.Column('send_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            'status',
            postgresql.ENUM(
                'pending', 'processing', 'sent', 'failed', 'cancelled',
                name='scheduledmessagestatus', create_type=False,
            ),
            nullable=False,
            server_default='pending',
        ),
        sa.Column('sent_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_scheduled_messages_id', 'scheduled_messages', ['id'])
    op.create_index('ix_scheduled_messages_send_at', 'scheduled_messages', ['send_at'])
    op.create_index('ix_scheduled_messages_status', 'scheduled_messages', ['status'])


def downgrade() -> None:
    op.drop_index('ix_scheduled_messages_status', table_name='scheduled_messages')
    op.drop_index('ix_scheduled_messages_send_at', table_name='scheduled_messages')
    op.drop_index('ix_scheduled_messages_id', table_name='scheduled_messages')
    op.drop_table('scheduled_messages')
    op.execute("DROP TYPE IF EXISTS scheduledmessagestatus")
