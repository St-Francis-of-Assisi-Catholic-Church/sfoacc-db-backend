"""add login_method to users

Revision ID: c2d3e4f5a6b7
Revises: b1c2d3e4f5a6
Create Date: 2026-03-15 00:00:00.000000

Adds:
  - users.login_method  (varchar 20, not null, default 'password')

Valid values: 'password' | 'email_otp' | 'sms_otp'
Existing rows default to 'password'.
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = 'c2d3e4f5a6b7'
down_revision: Union[str, None] = 'b1c2d3e4f5a6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        'users',
        sa.Column(
            'login_method',
            sa.String(20),
            nullable=False,
            server_default='PASSWORD',
        ),
    )


def downgrade() -> None:
    op.drop_column('users', 'login_method')
