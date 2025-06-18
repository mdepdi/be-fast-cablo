"""Remove lastmile_request_details table and add download_links column

Revision ID: 002
Revises: 001
Create Date: 2024-12-19 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '002'
down_revision = '001'
branch_labels = None
depends_on = None


def upgrade():
    """Upgrade database schema"""

    # Add download_links column to lastmile_processing_results
    op.add_column('lastmile_processing_results',
                  sa.Column('download_links', postgresql.JSONB(astext_type=sa.Text()), nullable=True))

    # Add comment for the new column
    op.execute("COMMENT ON COLUMN lastmile_processing_results.download_links IS 'Download URLs for output files as JSONB'")

    # Drop the unused lastmile_request_details table
    # First drop the trigger
    op.execute("DROP TRIGGER IF EXISTS update_lastmile_request_details_updated_at ON lastmile_request_details")

    # Drop indexes
    op.drop_index('ix_lastmile_request_details_ne_name', table_name='lastmile_request_details')
    op.drop_index('ix_lastmile_request_details_fe_name', table_name='lastmile_request_details')
    op.drop_index('ix_lastmile_request_details_sequence', table_name='lastmile_request_details')
    op.drop_index('ix_lastmile_request_details_processing_result_id', table_name='lastmile_request_details')
    op.drop_index('ix_lastmile_request_details_id', table_name='lastmile_request_details')

    # Drop the table
    op.drop_table('lastmile_request_details')


def downgrade():
    """Downgrade database schema"""

    # Recreate lastmile_request_details table
    op.create_table('lastmile_request_details',
        sa.Column('id', postgresql.UUID(), nullable=False),
        sa.Column('processing_result_id', postgresql.UUID(), nullable=False),
        sa.Column('request_sequence', sa.Integer(), nullable=False),
        sa.Column('fe_name', sa.String(length=255), nullable=False),
        sa.Column('ne_name', sa.String(length=255), nullable=False),
        sa.Column('fe_latitude', sa.Float(), nullable=False),
        sa.Column('fe_longitude', sa.Float(), nullable=False),
        sa.Column('ne_latitude', sa.Float(), nullable=False),
        sa.Column('ne_longitude', sa.Float(), nullable=False),
        sa.Column('segment_count', sa.Integer(), nullable=True),
        sa.Column('total_distance_m', sa.Float(), nullable=True),
        sa.Column('overlapped_distance_m', sa.Float(), nullable=True),
        sa.Column('new_build_distance_m', sa.Float(), nullable=True),
        sa.Column('overlapped_percentage', sa.Float(), nullable=True),
        sa.Column('new_build_percentage', sa.Float(), nullable=True),
        sa.Column('processing_status', sa.String(length=50), nullable=False),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('request_geometry', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['processing_result_id'], ['lastmile_processing_results.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )

    # Recreate indexes
    op.create_index('ix_lastmile_request_details_id', 'lastmile_request_details', ['id'])
    op.create_index('ix_lastmile_request_details_processing_result_id', 'lastmile_request_details', ['processing_result_id'])
    op.create_index('ix_lastmile_request_details_sequence', 'lastmile_request_details', ['request_sequence'])
    op.create_index('ix_lastmile_request_details_fe_name', 'lastmile_request_details', ['fe_name'])
    op.create_index('ix_lastmile_request_details_ne_name', 'lastmile_request_details', ['ne_name'])

    # Add comments
    op.execute("COMMENT ON COLUMN lastmile_request_details.processing_result_id IS 'Reference to main processing result'")
    op.execute("COMMENT ON COLUMN lastmile_request_details.request_sequence IS 'Sequence number of this request'")
    op.execute("COMMENT ON COLUMN lastmile_request_details.fe_name IS 'Far End name'")
    op.execute("COMMENT ON COLUMN lastmile_request_details.ne_name IS 'Near End name'")
    op.execute("COMMENT ON COLUMN lastmile_request_details.fe_latitude IS 'Far End latitude'")
    op.execute("COMMENT ON COLUMN lastmile_request_details.fe_longitude IS 'Far End longitude'")
    op.execute("COMMENT ON COLUMN lastmile_request_details.ne_latitude IS 'Near End latitude'")
    op.execute("COMMENT ON COLUMN lastmile_request_details.ne_longitude IS 'Near End longitude'")
    op.execute("COMMENT ON COLUMN lastmile_request_details.segment_count IS 'Number of segments generated'")
    op.execute("COMMENT ON COLUMN lastmile_request_details.total_distance_m IS 'Total distance in meters'")
    op.execute("COMMENT ON COLUMN lastmile_request_details.overlapped_distance_m IS 'Overlapped distance in meters'")
    op.execute("COMMENT ON COLUMN lastmile_request_details.new_build_distance_m IS 'New build distance in meters'")
    op.execute("COMMENT ON COLUMN lastmile_request_details.overlapped_percentage IS 'Overlapped percentage'")
    op.execute("COMMENT ON COLUMN lastmile_request_details.new_build_percentage IS 'New build percentage'")
    op.execute("COMMENT ON COLUMN lastmile_request_details.processing_status IS 'Individual request status'")
    op.execute("COMMENT ON COLUMN lastmile_request_details.error_message IS 'Error message for this specific request'")
    op.execute("COMMENT ON COLUMN lastmile_request_details.request_geometry IS 'GeoJSON geometry for this specific request'")

    # Set default value
    op.execute("ALTER TABLE lastmile_request_details ALTER COLUMN processing_status SET DEFAULT 'pending'")

    # Recreate trigger
    trigger_sql = """
    CREATE TRIGGER update_lastmile_request_details_updated_at
    BEFORE UPDATE ON lastmile_request_details
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();
    """
    op.execute(trigger_sql)

    # Remove download_links column from lastmile_processing_results
    op.drop_column('lastmile_processing_results', 'download_links')