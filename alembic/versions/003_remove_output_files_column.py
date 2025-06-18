"""Remove output_files column from lastmile_processing_results

Revision ID: 003_remove_output_files_column
Revises: 002_remove_request_details_add_download_links
Create Date: 2024-06-17 16:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '003'
down_revision = '002'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Remove output_files column from lastmile_processing_results table"""
    # Remove the output_files column
    op.drop_column('lastmile_processing_results', 'output_files')


def downgrade() -> None:
    """Add back output_files column to lastmile_processing_results table"""
    # Add back the output_files column
    op.add_column('lastmile_processing_results',
                  sa.Column('output_files', postgresql.JSONB(astext_type=sa.Text()), nullable=True))

    # Add back the comment
    op.execute("COMMENT ON COLUMN lastmile_processing_results.output_files IS 'List of generated output files'")