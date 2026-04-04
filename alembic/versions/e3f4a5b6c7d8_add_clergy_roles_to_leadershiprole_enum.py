"""add clergy roles to leadershiprole enum

Revision ID: e3f4a5b6c7d8
Revises: d1e2f3a4b5c6
Branch Labels: None
Depends On: None

The leadershiprole enum was originally created by the societies migration with
society-officer values (PRESIDENT, VICE_PRESIDENT, etc.). The church_unit_leadership
migration used checkfirst=True and was silently skipped, leaving the column unable
to store clergy roles. This migration adds the missing values.
"""
from typing import Sequence, Union
from alembic import op

revision: str = 'e3f4a5b6c7d8'
down_revision: Union[str, None] = ('d1e2f3a4b5c6', 'f3a4b5c6d7e8')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

CLERGY_VALUES = [
    'priest_in_charge',
    'assistant_priest',
    'deacon',
    'church_administrator',
    'church_secretary',
    'ppc_chairman',
    'ppc_vice_chairman',
    'ppc_secretary',
    'ppc_treasurer',
    'ppc_member',
    'other',
]


def upgrade() -> None:
    for value in CLERGY_VALUES:
        op.execute(f"ALTER TYPE leadershiprole ADD VALUE IF NOT EXISTS '{value}'")


def downgrade() -> None:
    # PostgreSQL does not support removing enum values without recreating the type.
    # Downgrade is intentionally a no-op.
    pass
