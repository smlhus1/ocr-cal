"""Initial schema - upload_analytics and feedback_log tables.

Revision ID: 001
Revises: None
Create Date: 2026-02-11

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

# revision identifiers, used by Alembic.
revision: str = '001'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create uuid-ossp extension
    op.execute('CREATE EXTENSION IF NOT EXISTS "uuid-ossp"')

    # upload_analytics table
    op.create_table(
        'upload_analytics',
        sa.Column('id', UUID(as_uuid=True), primary_key=True, server_default=sa.text('uuid_generate_v4()')),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('NOW()')),
        sa.Column('file_format', sa.String(10), nullable=False),
        sa.Column('file_size_kb', sa.Integer()),
        sa.Column('ocr_engine', sa.String(20)),
        sa.Column('shifts_found', sa.Integer()),
        sa.Column('confidence_score', sa.Float()),
        sa.Column('processing_time_ms', sa.Integer()),
        sa.Column('success', sa.Boolean(), nullable=False, server_default=sa.text('FALSE')),
        sa.Column('error_type', sa.String(50)),
        sa.Column('country_code', sa.CHAR(2)),
        sa.Column('blob_id', sa.String(100)),
        sa.Column('expires_at', sa.DateTime(), nullable=False),
    )
    op.create_index('idx_created_at', 'upload_analytics', ['created_at'])
    op.create_index('idx_expires_at', 'upload_analytics', ['expires_at'])
    op.create_index('idx_file_format', 'upload_analytics', ['file_format'])
    op.create_index('idx_success', 'upload_analytics', ['success'])

    # feedback_log table
    op.create_table(
        'feedback_log',
        sa.Column('id', UUID(as_uuid=True), primary_key=True, server_default=sa.text('uuid_generate_v4()')),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('NOW()')),
        sa.Column('upload_id', UUID(as_uuid=True), nullable=False),
        sa.Column('error_type', sa.String(50), nullable=False),
        sa.Column('correction_pattern', sa.String(500)),
    )
    op.create_index('idx_feedback_error_type', 'feedback_log', ['error_type'])
    op.create_index('idx_feedback_created_at', 'feedback_log', ['created_at'])

    # Cleanup function
    op.execute("""
        CREATE OR REPLACE FUNCTION cleanup_expired_records()
        RETURNS INTEGER AS $$
        DECLARE
            deleted_count INTEGER;
        BEGIN
            DELETE FROM upload_analytics
            WHERE expires_at < NOW();
            GET DIAGNOSTICS deleted_count = ROW_COUNT;
            RETURN deleted_count;
        END;
        $$ LANGUAGE plpgsql;
    """)


def downgrade() -> None:
    op.execute('DROP FUNCTION IF EXISTS cleanup_expired_records()')
    op.drop_table('feedback_log')
    op.drop_table('upload_analytics')
