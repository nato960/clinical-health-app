"""0002_update_speciality_enum_to_english

Revision ID: 0002
Revises: 0001
Create Date: 2026-06-30

"""
from typing import Sequence, Union

from alembic import op


revision: str = '0002'
down_revision: Union[str, Sequence[str], None] = '0001'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("ALTER TYPE speciality RENAME VALUE 'CARDIOLOGISTA' TO 'CARDIOLOGY'")
    op.execute("ALTER TYPE speciality RENAME VALUE 'DERMATOLOGIA' TO 'DERMATOLOGY'")
    op.execute("ALTER TYPE speciality RENAME VALUE 'ORTOPEDIA' TO 'ORTHOPEDICS'")
    op.execute("ALTER TYPE speciality RENAME VALUE 'PEDIATRIA' TO 'PEDIATRICS'")
    op.execute("ALTER TYPE speciality RENAME VALUE 'PSIQUIATRIA' TO 'PSYCHIATRY'")
    op.execute("ALTER TYPE speciality RENAME VALUE 'GINECOLOGIA' TO 'GYNECOLOGY'")
    op.execute("ALTER TYPE speciality RENAME VALUE 'NEUROLOGIA' TO 'NEUROLOGY'")
    op.execute("ALTER TYPE speciality ADD VALUE 'GENERAL_PRACTICE'")
    op.execute("ALTER TYPE speciality ADD VALUE 'UROLOGY'")


def downgrade() -> None:
    # ADD VALUE cannot be reversed in PostgreSQL without recreating the type.
    # Doctors with GENERAL_PRACTICE or UROLOGY must be updated before downgrading.
    op.execute("ALTER TYPE speciality RENAME VALUE 'CARDIOLOGY' TO 'CARDIOLOGISTA'")
    op.execute("ALTER TYPE speciality RENAME VALUE 'DERMATOLOGY' TO 'DERMATOLOGIA'")
    op.execute("ALTER TYPE speciality RENAME VALUE 'ORTHOPEDICS' TO 'ORTOPEDIA'")
    op.execute("ALTER TYPE speciality RENAME VALUE 'PEDIATRICS' TO 'PEDIATRIA'")
    op.execute("ALTER TYPE speciality RENAME VALUE 'PSYCHIATRY' TO 'PSIQUIATRIA'")
    op.execute("ALTER TYPE speciality RENAME VALUE 'GYNECOLOGY' TO 'GINECOLOGIA'")
    op.execute("ALTER TYPE speciality RENAME VALUE 'NEUROLOGY' TO 'NEUROLOGIA'")
