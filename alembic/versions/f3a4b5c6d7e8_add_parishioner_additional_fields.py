"""add parishioner additional fields

Revision ID: f3a4b5c6d7e8
Revises: e2f3a4b5c6d7
Create Date: 2026-03-15 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = 'f3a4b5c6d7e8'
down_revision: Union[str, None] = 'e2f3a4b5c6d7'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('parishioners', sa.Column('title', sa.String(length=20), nullable=True))
    op.add_column('parishioners', sa.Column('baptismal_name', sa.String(length=100), nullable=True))
    op.add_column('parishioners', sa.Column('nationality', sa.String(length=100), nullable=True))
    op.add_column('parishioners', sa.Column('is_deceased', sa.Boolean(), nullable=False, server_default='false'))
    op.add_column('parishioners', sa.Column('date_of_death', sa.Date(), nullable=True))
    op.add_column('parishioners', sa.Column('photo_url', sa.String(length=500), nullable=True))
    op.add_column('parishioners', sa.Column('notes', sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column('parishioners', 'notes')
    op.drop_column('parishioners', 'photo_url')
    op.drop_column('parishioners', 'date_of_death')
    op.drop_column('parishioners', 'is_deceased')
    op.drop_column('parishioners', 'nationality')
    op.drop_column('parishioners', 'baptismal_name')
    op.drop_column('parishioners', 'title')
