"""0005_add_appointment_doctor_slot_unique_index

Revision ID: 0005
Revises: 0004
Create Date: 2026-07-06

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '0005'
down_revision: Union[str, Sequence[str], None] = '0004'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_index(
        'uq_appointment_doctor_active_slot',
        'appointments',
        ['doctor_id', 'date'],
        unique=True,
        postgresql_where=sa.text('cancellation_reason IS NULL'),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index('uq_appointment_doctor_active_slot', table_name='appointments')
