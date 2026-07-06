"""0004_create_appointments_table

Revision ID: 0004
Revises: 0003
Create Date: 2026-07-03

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = '0004'
down_revision: Union[str, Sequence[str], None] = '0003'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    speciality_enum = postgresql.ENUM(
        'CARDIOLOGY', 'DERMATOLOGY', 'ORTHOPEDICS', 'PEDIATRICS', 'PSYCHIATRY',
        'GYNECOLOGY', 'NEUROLOGY', 'GENERAL_PRACTICE', 'UROLOGY',
        name='speciality',
        create_type=False,
    )

    op.create_table('appointments',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('doctor_id', sa.Integer(), nullable=False),
    sa.Column('patient_id', sa.Integer(), nullable=False),
    sa.Column('date', sa.DateTime(), nullable=False),
    sa.Column('speciality', speciality_enum, nullable=True),
    sa.Column('cancellation_reason', sa.Enum('PATIENT_CANCELED', 'DOCTOR_CANCELED', 'OTHER', name='cancellationreason'), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.ForeignKeyConstraint(['doctor_id'], ['doctors.id'], ),
    sa.ForeignKeyConstraint(['patient_id'], ['patients.id'], ),
    sa.PrimaryKeyConstraint('id')
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_table('appointments')
    op.execute("DROP TYPE cancellationreason")
