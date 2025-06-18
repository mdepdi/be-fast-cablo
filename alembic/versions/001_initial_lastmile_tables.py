"""Initial LastMile Processing Tables

Revision ID: 001
Revises:
Create Date: 2024-12-19 10:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '001'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create lastmile_processing_results table
    op.create_table('lastmile_processing_results',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('request_id', sa.String(length=255), nullable=False),
        sa.Column('input_filename', sa.String(length=500), nullable=True),
        sa.Column('total_requests', sa.Integer(), nullable=True),
        sa.Column('processed_requests', sa.Integer(), nullable=True),
        sa.Column('processing_status', sa.String(length=50), nullable=False),
        sa.Column('processing_started_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('processing_completed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('processing_duration_seconds', sa.Integer(), nullable=True),
        sa.Column('pulau', sa.String(length=100), nullable=True),
        sa.Column('ors_base_url', sa.String(length=500), nullable=True),
        sa.Column('graph_path', sa.String(length=500), nullable=True),
        sa.Column('result_analysis', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('summary_analysis', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('output_files', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('error_details', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('created_by', sa.String(length=255), nullable=True),
        sa.Column('metadata_info', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )

    # Create indexes for better query performance
    op.create_index('ix_lastmile_processing_results_id', 'lastmile_processing_results', ['id'])
    op.create_index('ix_lastmile_processing_results_request_id', 'lastmile_processing_results', ['request_id'])
    op.create_index('ix_lastmile_processing_results_status', 'lastmile_processing_results', ['processing_status'])
    op.create_index('ix_lastmile_processing_results_created_at', 'lastmile_processing_results', ['created_at'])
    op.create_index('ix_lastmile_processing_results_pulau', 'lastmile_processing_results', ['pulau'])

    # Add comments to columns
    op.execute("COMMENT ON COLUMN lastmile_processing_results.request_id IS 'Unique request identifier'")
    op.execute("COMMENT ON COLUMN lastmile_processing_results.input_filename IS 'Original input file name'")
    op.execute("COMMENT ON COLUMN lastmile_processing_results.total_requests IS 'Total number of requests processed'")
    op.execute("COMMENT ON COLUMN lastmile_processing_results.processed_requests IS 'Number of successfully processed requests'")
    op.execute("COMMENT ON COLUMN lastmile_processing_results.processing_status IS 'Status: pending, processing, completed, failed'")
    op.execute("COMMENT ON COLUMN lastmile_processing_results.processing_started_at IS 'When processing started'")
    op.execute("COMMENT ON COLUMN lastmile_processing_results.processing_completed_at IS 'When processing completed'")
    op.execute("COMMENT ON COLUMN lastmile_processing_results.processing_duration_seconds IS 'Total processing time in seconds'")
    op.execute("COMMENT ON COLUMN lastmile_processing_results.pulau IS 'Island name used for processing'")
    op.execute("COMMENT ON COLUMN lastmile_processing_results.ors_base_url IS 'ORS server URL used'")
    op.execute("COMMENT ON COLUMN lastmile_processing_results.graph_path IS 'Path to graph file used'")
    op.execute("COMMENT ON COLUMN lastmile_processing_results.result_analysis IS 'Complete geodataframe results as GeoJSON'")
    op.execute("COMMENT ON COLUMN lastmile_processing_results.summary_analysis IS 'Summary statistics and analysis'")
    op.execute("COMMENT ON COLUMN lastmile_processing_results.output_files IS 'List of generated output files'")
    op.execute("COMMENT ON COLUMN lastmile_processing_results.error_message IS 'Error message if processing failed'")
    op.execute("COMMENT ON COLUMN lastmile_processing_results.error_details IS 'Detailed error information'")
    op.execute("COMMENT ON COLUMN lastmile_processing_results.created_by IS 'User or system that created this record'")
    op.execute("COMMENT ON COLUMN lastmile_processing_results.metadata_info IS 'Additional metadata and configuration'")

    # Create lastmile_request_details table
    op.create_table('lastmile_request_details',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('processing_result_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('request_sequence', sa.Integer(), nullable=False),
        sa.Column('fe_name', sa.String(length=255), nullable=True),
        sa.Column('ne_name', sa.String(length=255), nullable=True),
        sa.Column('fe_latitude', sa.String(length=50), nullable=True),
        sa.Column('fe_longitude', sa.String(length=50), nullable=True),
        sa.Column('ne_latitude', sa.String(length=50), nullable=True),
        sa.Column('ne_longitude', sa.String(length=50), nullable=True),
        sa.Column('segment_count', sa.Integer(), nullable=True),
        sa.Column('total_distance_m', sa.Integer(), nullable=True),
        sa.Column('overlapped_distance_m', sa.Integer(), nullable=True),
        sa.Column('new_build_distance_m', sa.Integer(), nullable=True),
        sa.Column('overlapped_percentage', sa.Integer(), nullable=True),
        sa.Column('new_build_percentage', sa.Integer(), nullable=True),
        sa.Column('processing_status', sa.String(length=50), nullable=False),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('request_geometry', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )

    # Create indexes for request details
    op.create_index('ix_lastmile_request_details_id', 'lastmile_request_details', ['id'])
    op.create_index('ix_lastmile_request_details_processing_result_id', 'lastmile_request_details', ['processing_result_id'])
    op.create_index('ix_lastmile_request_details_sequence', 'lastmile_request_details', ['request_sequence'])
    op.create_index('ix_lastmile_request_details_fe_name', 'lastmile_request_details', ['fe_name'])
    op.create_index('ix_lastmile_request_details_ne_name', 'lastmile_request_details', ['ne_name'])

    # Add comments to request details columns
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

    # Set default values
    op.execute("ALTER TABLE lastmile_processing_results ALTER COLUMN processing_status SET DEFAULT 'pending'")
    op.execute("ALTER TABLE lastmile_request_details ALTER COLUMN processing_status SET DEFAULT 'pending'")

    # Create trigger to automatically update updated_at timestamp
    op.execute("""
        CREATE OR REPLACE FUNCTION update_updated_at_column()
        RETURNS TRIGGER AS $$
        BEGIN
            NEW.updated_at = now();
            RETURN NEW;
        END;
        $$ language 'plpgsql';
    """)

    op.execute("""
        CREATE TRIGGER update_lastmile_processing_results_updated_at
        BEFORE UPDATE ON lastmile_processing_results
        FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
    """)

    op.execute("""
        CREATE TRIGGER update_lastmile_request_details_updated_at
        BEFORE UPDATE ON lastmile_request_details
        FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
    """)


def downgrade() -> None:
    # Drop triggers
    op.execute("DROP TRIGGER IF EXISTS update_lastmile_request_details_updated_at ON lastmile_request_details")
    op.execute("DROP TRIGGER IF EXISTS update_lastmile_processing_results_updated_at ON lastmile_processing_results")
    op.execute("DROP FUNCTION IF EXISTS update_updated_at_column()")

    # Drop tables
    op.drop_table('lastmile_request_details')
    op.drop_table('lastmile_processing_results')