"""add otp_codes table and users.phone

Revision ID: b1c2d3e4f5a6
Revises: f1b2c3d4e5f6
Create Date: 2026-03-15 00:00:00.000000

Adds:
  - users.phone  (nullable varchar 30)
  - otp_codes table  (user_id, code_hash, delivery, expires_at, used)

Auth settings are stored as ParishSettings rows (no schema change needed):
  auth.password_enabled   = "true"
  auth.otp_sms_enabled    = "false"
  auth.otp_email_enabled  = "false"
  auth.otp_expiry_minutes = "10"
  auth.otp_code_length    = "6"
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = 'b1c2d3e4f5a6'
down_revision: Union[str, None] = 'f1b2c3d4e5f6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ── users.phone ────────────────────────────────────────────────────────────
    op.add_column('users', sa.Column('phone', sa.String(30), nullable=True))
    op.create_index('ix_users_phone', 'users', ['phone'])

    # ── otp_codes ──────────────────────────────────────────────────────────────
    op.create_table(
        'otp_codes',
        sa.Column('id', sa.Integer, primary_key=True, autoincrement=True),
        sa.Column('user_id', sa.UUID(as_uuid=True),
                  sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('code_hash', sa.String(64), nullable=False),
        sa.Column('delivery', sa.String(10), nullable=False),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('used', sa.Boolean, nullable=False, server_default='false'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.func.now()),
    )
    op.create_index('ix_otp_codes_user_id', 'otp_codes', ['user_id'])
    op.create_index('ix_otp_codes_expires_at', 'otp_codes', ['expires_at'])

    # ── default auth settings ──────────────────────────────────────────────────
    # Inserted only if they don't exist — idempotent via ON CONFLICT DO NOTHING.
    op.execute("""
        INSERT INTO parish_settings (church_unit_id, key, value, label, description)
        SELECT
            cu.id,
            s.key,
            s.value,
            s.label,
            s.description
        FROM (VALUES
            ('auth.password_enabled',   'true',  'Password Login Enabled',   'Allow username + password login'),
            ('auth.otp_sms_enabled',    'false', 'OTP SMS Login Enabled',    'Allow passwordless login via SMS code'),
            ('auth.otp_email_enabled',  'false', 'OTP Email Login Enabled',  'Allow passwordless login via email code'),
            ('auth.otp_expiry_minutes', '10',    'OTP Code Expiry (minutes)','How long an OTP code is valid'),
            ('auth.otp_code_length',    '6',     'OTP Code Length',          'Number of digits in OTP code')
        ) AS s(key, value, label, description)
        CROSS JOIN (SELECT id FROM church_units WHERE type = 'PARISH' LIMIT 1) AS cu
        ON CONFLICT (key) DO NOTHING
    """)


def downgrade() -> None:
    op.drop_table('otp_codes')
    op.drop_index('ix_users_phone', table_name='users')
    op.drop_column('users', 'phone')
    op.execute("""
        DELETE FROM parish_settings
        WHERE key IN (
            'auth.password_enabled', 'auth.otp_sms_enabled', 'auth.otp_email_enabled',
            'auth.otp_expiry_minutes', 'auth.otp_code_length'
        )
    """)
