"""replace parish/outstation with church_unit

Revision ID: e1a2b3c4d5e6
Revises: c28688039760
Create Date: 2026-03-14 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = 'e1a2b3c4d5e6'
down_revision: Union[str, None] = 'c28688039760'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Create the ChurchUnitType enum (checkfirst=True handles re-runs)
    church_unit_type_enum = postgresql.ENUM('parish', 'outstation', name='churchunittype')
    church_unit_type_enum.create(op.get_bind(), checkfirst=True)

    # 2. Create church_units table with temp tracking columns for data migration
    op.create_table(
        'church_units',
        sa.Column('id', sa.Integer, primary_key=True, autoincrement=True),
        sa.Column('type', postgresql.ENUM('parish', 'outstation', name='churchunittype', create_type=False), nullable=False),
        sa.Column('parent_id', sa.Integer, sa.ForeignKey('church_units.id', ondelete='SET NULL'), nullable=True),
        sa.Column('name', sa.String(200), nullable=False),
        sa.Column('diocese', sa.String(200), nullable=True),
        sa.Column('address', sa.String(500), nullable=True),
        sa.Column('phone', sa.String(50), nullable=True),
        sa.Column('email', sa.String(200), nullable=True),
        sa.Column('website', sa.String(200), nullable=True),
        sa.Column('established_date', sa.Date, nullable=True),
        sa.Column('pastor_name', sa.String(200), nullable=True),
        sa.Column('pastor_email', sa.String(200), nullable=True),
        sa.Column('pastor_phone', sa.String(50), nullable=True),
        sa.Column('location_description', sa.String(500), nullable=True),
        sa.Column('google_maps_url', sa.String(500), nullable=True),
        sa.Column('latitude', sa.Float, nullable=True),
        sa.Column('longitude', sa.Float, nullable=True),
        sa.Column('priest_in_charge', sa.String(200), nullable=True),
        sa.Column('priest_phone', sa.String(50), nullable=True),
        sa.Column('is_active', sa.Boolean, nullable=False, server_default='true'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        # Temp columns to track old IDs during migration (dropped at end)
        sa.Column('_old_parish_id', sa.Integer, nullable=True),
        sa.Column('_old_outstation_id', sa.Integer, nullable=True),
    )
    op.create_index('ix_church_units_type', 'church_units', ['type'])
    op.create_index('ix_church_units_parent_id', 'church_units', ['parent_id'])

    # 3. Migrate parish data into church_units
    op.execute("""
        INSERT INTO church_units (
            type, name, diocese, address, phone, email, website,
            established_date, pastor_name, pastor_email, pastor_phone,
            is_active, created_at, updated_at, _old_parish_id
        )
        SELECT
            'parish'::churchunittype, name, diocese, address, phone, email, website,
            established_date, pastor_name, pastor_email, pastor_phone,
            TRUE, created_at, updated_at, id
        FROM parish
    """)

    # 4. Migrate outstations into church_units, linking parent via the mapping
    op.execute("""
        INSERT INTO church_units (
            type, parent_id, name, address, location_description,
            google_maps_url, latitude, longitude, phone, email,
            priest_in_charge, priest_phone, is_active,
            created_at, updated_at, _old_outstation_id
        )
        SELECT
            'outstation'::churchunittype,
            cu.id,
            o.name, o.address, o.location_description,
            o.google_maps_url, o.latitude, o.longitude,
            o.phone, o.email, o.priest_in_charge, o.priest_phone,
            o.is_active, o.created_at, o.updated_at, o.id
        FROM outstations o
        LEFT JOIN church_units cu ON cu._old_parish_id = o.parish_id
    """)

    # 5. Add church_unit_id to all dependent tables

    # societies
    op.add_column('societies', sa.Column('church_unit_id', sa.Integer,
                  sa.ForeignKey('church_units.id', ondelete='SET NULL'), nullable=True))
    op.execute("""
        UPDATE societies s
        SET church_unit_id = cu.id
        FROM church_units cu
        WHERE cu._old_outstation_id = s.outstation_id
    """)
    op.drop_constraint('societies_outstation_id_fkey', 'societies', type_='foreignkey')
    op.drop_index('ix_societies_outstation_id', table_name='societies')
    op.drop_column('societies', 'outstation_id')
    op.create_index('ix_societies_church_unit_id', 'societies', ['church_unit_id'])

    # church_communities
    op.add_column('church_communities', sa.Column('church_unit_id', sa.Integer,
                  sa.ForeignKey('church_units.id', ondelete='SET NULL'), nullable=True))
    op.execute("""
        UPDATE church_communities cc
        SET church_unit_id = cu.id
        FROM church_units cu
        WHERE cu._old_outstation_id = cc.outstation_id
    """)
    op.drop_constraint('church_communities_outstation_id_fkey', 'church_communities', type_='foreignkey')
    op.drop_index('ix_church_communities_outstation_id', table_name='church_communities')
    op.drop_column('church_communities', 'outstation_id')
    op.create_index('ix_church_communities_church_unit_id', 'church_communities', ['church_unit_id'])

    # parishioners
    op.add_column('parishioners', sa.Column('church_unit_id', sa.Integer,
                  sa.ForeignKey('church_units.id', ondelete='SET NULL'), nullable=True))
    op.execute("""
        UPDATE parishioners p
        SET church_unit_id = cu.id
        FROM church_units cu
        WHERE cu._old_outstation_id = p.outstation_id
    """)
    op.drop_constraint('parishioners_outstation_id_fkey', 'parishioners', type_='foreignkey')
    op.drop_index('ix_parishioners_outstation_id', table_name='parishioners')
    op.drop_column('parishioners', 'outstation_id')
    op.create_index('ix_parishioners_church_unit_id', 'parishioners', ['church_unit_id'])

    # users
    op.add_column('users', sa.Column('church_unit_id', sa.Integer,
                  sa.ForeignKey('church_units.id', ondelete='SET NULL'), nullable=True))
    op.execute("""
        UPDATE users u
        SET church_unit_id = cu.id
        FROM church_units cu
        WHERE cu._old_outstation_id = u.outstation_id
    """)
    op.drop_constraint('users_outstation_id_fkey', 'users', type_='foreignkey')
    op.drop_index('ix_users_outstation_id', table_name='users')
    op.drop_column('users', 'outstation_id')
    op.create_index('ix_users_church_unit_id', 'users', ['church_unit_id'])

    # parish_settings: was linked to parish, now to church_unit (parish type)
    op.add_column('parish_settings', sa.Column('church_unit_id', sa.Integer,
                  sa.ForeignKey('church_units.id', ondelete='CASCADE'), nullable=True))
    op.execute("""
        UPDATE parish_settings ps
        SET church_unit_id = cu.id
        FROM church_units cu
        WHERE cu._old_parish_id = ps.parish_id
    """)
    op.drop_constraint('parish_settings_parish_id_fkey', 'parish_settings', type_='foreignkey')
    op.drop_index('ix_parish_settings_parish_id', table_name='parish_settings')
    op.drop_column('parish_settings', 'parish_id')
    op.alter_column('parish_settings', 'church_unit_id', nullable=False)
    op.create_index('ix_parish_settings_church_unit_id', 'parish_settings', ['church_unit_id'])

    # mass_schedules: combine parish_id + outstation_id into church_unit_id
    op.add_column('mass_schedules', sa.Column('church_unit_id', sa.Integer,
                  sa.ForeignKey('church_units.id', ondelete='CASCADE'), nullable=True))
    op.execute("""
        UPDATE mass_schedules ms
        SET church_unit_id = cu.id
        FROM church_units cu
        WHERE cu._old_parish_id = ms.parish_id AND ms.parish_id IS NOT NULL
    """)
    op.execute("""
        UPDATE mass_schedules ms
        SET church_unit_id = cu.id
        FROM church_units cu
        WHERE cu._old_outstation_id = ms.outstation_id AND ms.outstation_id IS NOT NULL
          AND ms.church_unit_id IS NULL
    """)
    op.drop_constraint('mass_schedules_parish_id_fkey', 'mass_schedules', type_='foreignkey')
    op.drop_constraint('mass_schedules_outstation_id_fkey', 'mass_schedules', type_='foreignkey')
    op.drop_index('ix_mass_schedules_parish_id', table_name='mass_schedules')
    op.drop_index('ix_mass_schedules_outstation_id', table_name='mass_schedules')
    op.drop_column('mass_schedules', 'parish_id')
    op.drop_column('mass_schedules', 'outstation_id')
    # Make church_unit_id NOT NULL after data migration (orphaned rows get deleted first)
    op.execute("DELETE FROM mass_schedules WHERE church_unit_id IS NULL")
    op.alter_column('mass_schedules', 'church_unit_id', nullable=False)
    op.create_index('ix_mass_schedules_church_unit_id', 'mass_schedules', ['church_unit_id'])

    # 6. Drop temp tracking columns
    op.drop_column('church_units', '_old_parish_id')
    op.drop_column('church_units', '_old_outstation_id')

    # 7. Drop old tables
    op.drop_table('outstations')
    op.drop_table('parish')


def downgrade() -> None:
    # Recreate original tables
    op.create_table(
        'parish',
        sa.Column('id', sa.Integer, primary_key=True),
        sa.Column('name', sa.String(200), nullable=False),
        sa.Column('diocese', sa.String(200), nullable=True),
        sa.Column('address', sa.String(500), nullable=True),
        sa.Column('phone', sa.String(50), nullable=True),
        sa.Column('email', sa.String(200), nullable=True),
        sa.Column('website', sa.String(200), nullable=True),
        sa.Column('established_date', sa.Date, nullable=True),
        sa.Column('pastor_name', sa.String(200), nullable=True),
        sa.Column('pastor_email', sa.String(200), nullable=True),
        sa.Column('pastor_phone', sa.String(50), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_table(
        'outstations',
        sa.Column('id', sa.Integer, primary_key=True),
        sa.Column('parish_id', sa.Integer, sa.ForeignKey('parish.id', ondelete='CASCADE'), nullable=False),
        sa.Column('name', sa.String(200), nullable=False),
        sa.Column('address', sa.String(500), nullable=True),
        sa.Column('location_description', sa.String(500), nullable=True),
        sa.Column('google_maps_url', sa.String(500), nullable=True),
        sa.Column('latitude', sa.Float, nullable=True),
        sa.Column('longitude', sa.Float, nullable=True),
        sa.Column('phone', sa.String(50), nullable=True),
        sa.Column('email', sa.String(200), nullable=True),
        sa.Column('priest_in_charge', sa.String(200), nullable=True),
        sa.Column('priest_phone', sa.String(50), nullable=True),
        sa.Column('is_active', sa.Boolean, nullable=False, server_default='true'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )

    # Restore outstation_id columns (data migration not implemented for downgrade)
    for table in ('societies', 'church_communities', 'parishioners', 'users'):
        op.add_column(table, sa.Column('outstation_id', sa.Integer, nullable=True))

    op.add_column('parish_settings', sa.Column('parish_id', sa.Integer, nullable=True))
    op.add_column('mass_schedules', sa.Column('parish_id', sa.Integer, nullable=True))
    op.add_column('mass_schedules', sa.Column('outstation_id', sa.Integer, nullable=True))

    # Remove church_unit_id columns
    for table in ('societies', 'church_communities', 'parishioners', 'users', 'parish_settings', 'mass_schedules'):
        op.drop_column(table, 'church_unit_id')

    op.drop_table('church_units')
    op.execute("DROP TYPE IF EXISTS churchunittype")
