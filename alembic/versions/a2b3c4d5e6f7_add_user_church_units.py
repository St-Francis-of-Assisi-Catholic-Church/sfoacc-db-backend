"""add user_church_units junction table with per-unit role

Revision ID: a2b3c4d5e6f7
Revises: e3f4a5b6c7d8
Branch Labels: None
Depends On: None
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = 'a2b3c4d5e6f7'
down_revision: Union[str, None] = 'e3f4a5b6c7d8'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'user_church_units',
        sa.Column('user_id', sa.UUID(as_uuid=True),
                  sa.ForeignKey('users.id', ondelete='CASCADE'),
                  primary_key=True, nullable=False),
        sa.Column('church_unit_id', sa.Integer(),
                  sa.ForeignKey('church_units.id', ondelete='CASCADE'),
                  primary_key=True, nullable=False),
        sa.Column('role_id', sa.Integer(),
                  sa.ForeignKey('roles.id', ondelete='SET NULL'),
                  nullable=True),
    )
    op.create_index('ix_user_church_units_user_id', 'user_church_units', ['user_id'])
    op.create_index('ix_user_church_units_church_unit_id', 'user_church_units', ['church_unit_id'])


def downgrade() -> None:
    op.drop_index('ix_user_church_units_church_unit_id', table_name='user_church_units')
    op.drop_index('ix_user_church_units_user_id', table_name='user_church_units')
    op.drop_table('user_church_units')
