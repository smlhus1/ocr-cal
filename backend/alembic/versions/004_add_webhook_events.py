"""Add webhook_events table for idempotency.

Revision ID: 004
Revises: 003
Create Date: 2026-02-13

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '004'
down_revision: Union[str, None] = '003'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'webhook_events',
        sa.Column('event_id', sa.String(255), primary_key=True),
        sa.Column('event_type', sa.String(100), nullable=False),
        sa.Column(
            'processed_at',
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )
    op.create_index('ix_webhook_events_processed_at', 'webhook_events', ['processed_at'])


def downgrade() -> None:
    op.drop_index('ix_webhook_events_processed_at', table_name='webhook_events')
    op.drop_table('webhook_events')
