"""Add session_id to upload_analytics and anonymous_sessions table.

Revision ID: 002
Revises: 001
Create Date: 2026-02-11

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

# revision identifiers, used by Alembic.
revision: str = '002'
down_revision: Union[str, None] = '001'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add session_id to upload_analytics
    op.add_column('upload_analytics', sa.Column('session_id', sa.String(36)))
    op.create_index('idx_session_id', 'upload_analytics', ['session_id'])

    # Create anonymous_sessions table
    op.create_table(
        'anonymous_sessions',
        sa.Column('session_id', sa.String(36), primary_key=True),
        sa.Column('stripe_subscription_id', sa.String(255), nullable=True),
        sa.Column('status', sa.String(20), nullable=False, server_default='free'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('NOW()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('NOW()')),
    )


def downgrade() -> None:
    op.drop_table('anonymous_sessions')
    op.drop_index('idx_session_id', table_name='upload_analytics')
    op.drop_column('upload_analytics', 'session_id')
