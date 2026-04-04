"""rename stations to outstations and update all fk columns

Revision ID: 04e9cbc3c0ed
Revises: 92b9019ef6af
Create Date: 2026-03-13 17:40:13.443553

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '04e9cbc3c0ed'
down_revision: Union[str, None] = '92b9019ef6af'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Drop all FK constraints that reference stations before renaming the table
    op.drop_constraint('mass_schedules_station_id_fkey', 'mass_schedules', type_='foreignkey')
    op.drop_constraint('church_communities_station_id_fkey', 'church_communities', type_='foreignkey')
    op.drop_constraint('parishioners_station_id_fkey', 'parishioners', type_='foreignkey')
    op.drop_constraint('societies_station_id_fkey', 'societies', type_='foreignkey')
    op.drop_constraint('users_station_id_fkey', 'users', type_='foreignkey')

    # 2. Rename the table (data is preserved)
    op.rename_table('stations', 'outstations')

    # 3. Rename the PostgreSQL enum type
    op.execute("ALTER TYPE stationtype RENAME TO outstationtype")

    # 4. Rename the table's own indexes
    op.drop_index('ix_stations_id', table_name='outstations')
    op.drop_index('ix_stations_parish_id', table_name='outstations')
    op.create_index(op.f('ix_outstations_id'), 'outstations', ['id'], unique=False)
    op.create_index(op.f('ix_outstations_parish_id'), 'outstations', ['parish_id'], unique=False)

    # 5. mass_schedules: rename column + indexes + FK
    op.drop_index('ix_mass_schedules_station_id', table_name='mass_schedules')
    op.alter_column('mass_schedules', 'station_id', new_column_name='outstation_id')
    op.create_index(op.f('ix_mass_schedules_outstation_id'), 'mass_schedules', ['outstation_id'], unique=False)
    op.create_foreign_key(None, 'mass_schedules', 'outstations', ['outstation_id'], ['id'], ondelete='CASCADE')

    # 6. church_communities: rename column + indexes + FK
    op.drop_index('ix_church_communities_station_id', table_name='church_communities')
    op.alter_column('church_communities', 'station_id', new_column_name='outstation_id')
    op.create_index(op.f('ix_church_communities_outstation_id'), 'church_communities', ['outstation_id'], unique=False)
    op.create_foreign_key(None, 'church_communities', 'outstations', ['outstation_id'], ['id'], ondelete='SET NULL')

    # 7. parishioners: rename column + indexes + FK
    op.drop_index('ix_parishioners_station_id', table_name='parishioners')
    op.alter_column('parishioners', 'station_id', new_column_name='outstation_id')
    op.create_index(op.f('ix_parishioners_outstation_id'), 'parishioners', ['outstation_id'], unique=False)
    op.create_foreign_key(None, 'parishioners', 'outstations', ['outstation_id'], ['id'], ondelete='SET NULL')

    # 8. societies: rename column + indexes + FK
    op.drop_index('ix_societies_station_id', table_name='societies')
    op.alter_column('societies', 'station_id', new_column_name='outstation_id')
    op.create_index(op.f('ix_societies_outstation_id'), 'societies', ['outstation_id'], unique=False)
    op.create_foreign_key(None, 'societies', 'outstations', ['outstation_id'], ['id'], ondelete='SET NULL')

    # 9. users: rename column + indexes + FK
    op.drop_index('ix_users_station_id', table_name='users')
    op.alter_column('users', 'station_id', new_column_name='outstation_id')
    op.create_index(op.f('ix_users_outstation_id'), 'users', ['outstation_id'], unique=False)
    op.create_foreign_key(None, 'users', 'outstations', ['outstation_id'], ['id'], ondelete='SET NULL')

    # 10. Add admin:outstation and admin:outstations permissions (rename admin:stations code)
    op.execute("UPDATE permissions SET code = 'admin:outstations', name = 'Manage All Outstations' WHERE code = 'admin:stations'")
    op.execute("INSERT INTO permissions (code, name, module) VALUES ('admin:outstation', 'Manage Own Outstation', 'admin') ON CONFLICT DO NOTHING")


def downgrade() -> None:
    # Reverse: rename outstation_id → station_id everywhere, rename table back
    op.execute("DELETE FROM permissions WHERE code = 'admin:outstation'")
    op.execute("UPDATE permissions SET code = 'admin:stations', name = 'Manage Stations' WHERE code = 'admin:outstations'")

    op.drop_constraint(None, 'users', type_='foreignkey')
    op.drop_index(op.f('ix_users_outstation_id'), table_name='users')
    op.alter_column('users', 'outstation_id', new_column_name='station_id')
    op.create_index('ix_users_station_id', 'users', ['station_id'], unique=False)

    op.drop_constraint(None, 'societies', type_='foreignkey')
    op.drop_index(op.f('ix_societies_outstation_id'), table_name='societies')
    op.alter_column('societies', 'outstation_id', new_column_name='station_id')
    op.create_index('ix_societies_station_id', 'societies', ['station_id'], unique=False)

    op.drop_constraint(None, 'parishioners', type_='foreignkey')
    op.drop_index(op.f('ix_parishioners_outstation_id'), table_name='parishioners')
    op.alter_column('parishioners', 'outstation_id', new_column_name='station_id')
    op.create_index('ix_parishioners_station_id', 'parishioners', ['station_id'], unique=False)

    op.drop_constraint(None, 'church_communities', type_='foreignkey')
    op.drop_index(op.f('ix_church_communities_outstation_id'), table_name='church_communities')
    op.alter_column('church_communities', 'outstation_id', new_column_name='station_id')
    op.create_index('ix_church_communities_station_id', 'church_communities', ['station_id'], unique=False)

    op.drop_constraint(None, 'mass_schedules', type_='foreignkey')
    op.drop_index(op.f('ix_mass_schedules_outstation_id'), table_name='mass_schedules')
    op.alter_column('mass_schedules', 'outstation_id', new_column_name='station_id')
    op.create_index('ix_mass_schedules_station_id', 'mass_schedules', ['station_id'], unique=False)

    op.drop_index(op.f('ix_outstations_id'), table_name='outstations')
    op.drop_index(op.f('ix_outstations_parish_id'), table_name='outstations')
    op.rename_table('outstations', 'stations')
    op.execute("ALTER TYPE outstationtype RENAME TO stationtype")
    op.create_index('ix_stations_id', 'stations', ['id'], unique=False)
    op.create_index('ix_stations_parish_id', 'stations', ['parish_id'], unique=False)

    op.create_foreign_key('mass_schedules_station_id_fkey', 'mass_schedules', 'stations', ['station_id'], ['id'], ondelete='CASCADE')
    op.create_foreign_key('church_communities_station_id_fkey', 'church_communities', 'stations', ['station_id'], ['id'], ondelete='SET NULL')
    op.create_foreign_key('parishioners_station_id_fkey', 'parishioners', 'stations', ['station_id'], ['id'], ondelete='SET NULL')
    op.create_foreign_key('societies_station_id_fkey', 'societies', 'stations', ['station_id'], ['id'], ondelete='SET NULL')
    op.create_foreign_key('users_station_id_fkey', 'users', 'stations', ['station_id'], ['id'], ondelete='SET NULL')
