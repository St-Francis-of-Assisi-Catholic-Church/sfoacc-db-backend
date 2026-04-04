"""add message_templates table

Revision ID: f4a5b6c7d8e9
Revises: f3a4b5c6d7e8
Create Date: 2026-03-20
"""

from alembic import op
import sqlalchemy as sa

revision = "f4a5b6c7d8e9"
down_revision = "a2b3c4d5e6f7"
branch_labels = None
depends_on = None

_SYSTEM_TEMPLATES = [
    (
        "main_welcome_message",
        "Welcome Message",
        "Hi {parishioner_name}, Welcome to {church_name}! We're blessed to have you join our community. For any inquiries, please contact us at {church_contact}.",
        "Sent when a parishioner is first created.",
        True,
    ),
    (
        "church_id_generation_message",
        "New Church ID Notification",
        "Hi {parishioner_name}, your new church ID: {new_church_id} has been generated successfully. Please keep this for your records. Thank you!",
        "Sent after a parishioner's church ID is generated.",
        True,
    ),
    (
        "parishioner_onboarding_welcome_message",
        "Parishioner Onboarding Message",
        "Dear {parishioner_name}, welcome to {church_name}! Your church records are being created. We will update you once the process is done. For any inquiries, contact us at {church_contact}.",
        "Sent during parishioner onboarding.",
        True,
    ),
    (
        "record_verification_message",
        "Record Verification Request",
        "Hi {parishioner_name}, verify your church records: {verification_link}\nCode: your date of birth (DDMMYYYY). Expires in 48hrs.",
        "Sent to prompt a parishioner to verify their record.",
        True,
    ),
    (
        "record_verification_confirmation_message",
        "Record Verification Confirmed",
        "Hi {parishioner_name}, thank you for verifying your church records. Your information has been successfully confirmed in our system. Thank you!",
        "Sent after a parishioner confirms their record.",
        True,
    ),
    (
        "event_reminder",
        "Event Reminder",
        "Dear {parishioner_name}, this is a reminder about {event_name} on {event_date} at {event_time}. We look forward to seeing you there.",
        "Sent to remind parishioners of an upcoming event.",
        True,
    ),
]


def upgrade() -> None:
    op.create_table(
        "message_templates",
        sa.Column("id", sa.String(100), primary_key=True),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("content", sa.Text, nullable=False),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column("is_system", sa.Boolean, nullable=False, server_default="false"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )

    templates_table = sa.table(
        "message_templates",
        sa.column("id", sa.String),
        sa.column("name", sa.String),
        sa.column("content", sa.Text),
        sa.column("description", sa.Text),
        sa.column("is_system", sa.Boolean),
    )
    op.bulk_insert(
        templates_table,
        [
            {"id": tid, "name": name, "content": content, "description": desc, "is_system": is_sys}
            for tid, name, content, desc, is_sys in _SYSTEM_TEMPLATES
        ],
    )


def downgrade() -> None:
    op.drop_table("message_templates")
