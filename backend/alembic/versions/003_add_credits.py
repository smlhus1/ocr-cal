"""Add credits column to anonymous_sessions.

Revision ID: 003
Revises: 002
Create Date: 2026-02-13

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '003'
down_revision: Union[str, None] = '002'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        'anonymous_sessions',
        sa.Column('credits', sa.Integer(), nullable=False, server_default='0')
    )


def downgrade() -> None:
    op.drop_column('anonymous_sessions', 'credits')
