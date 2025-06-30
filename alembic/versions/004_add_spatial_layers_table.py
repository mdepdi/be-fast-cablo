"""add spatial layers table

Revision ID: 004_add_spatial_layers_table
Revises: 003_remove_output_files_column
Create Date: 2024-01-01 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB, UUID


# revision identifiers, used by Alembic.
revision = '004'
down_revision = '003'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Add spatial_layers table"""
    op.create_table(
        'spatial_layers',
        sa.Column('id', UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('layer_name', sa.String(255), nullable=False, unique=True, index=True, comment="Unique layer name (also table name)"),
        sa.Column('display_name', sa.String(255), nullable=False, comment="Human-readable display name"),
        sa.Column('description', sa.Text, nullable=True, comment="Layer description"),

        # File metadata
        sa.Column('original_filename', sa.String(500), nullable=False, comment="Original uploaded file name"),
        sa.Column('file_type', sa.String(50), nullable=False, comment="File type: parquet, geoparquet, etc."),
        sa.Column('file_size_bytes', sa.Integer, nullable=True, comment="File size in bytes"),

        # Spatial metadata
        sa.Column('geometry_type', sa.String(50), nullable=True, comment="Geometry type: Point, LineString, Polygon, etc."),
        sa.Column('srid', sa.Integer, nullable=False, default=4326, comment="Spatial Reference System Identifier"),
        sa.Column('bbox', JSONB, nullable=True, comment="Bounding box coordinates [minx, miny, maxx, maxy]"),
        sa.Column('feature_count', sa.Integer, nullable=True, comment="Number of features in the layer"),

        # Martin tile service
        sa.Column('martin_layer_id', sa.String(255), nullable=True, comment="Layer ID in Martin tile service"),
        sa.Column('martin_url', sa.String(500), nullable=True, comment="Martin tile service URL for this layer"),

        # MapLibre styling
        sa.Column('maplibre_style', JSONB, nullable=False, server_default='{}', comment="MapLibre GL style specification for this layer"),
        sa.Column('default_visibility', sa.Boolean, nullable=False, default=True, comment="Default visibility state"),
        sa.Column('min_zoom', sa.Integer, nullable=True, default=0, comment="Minimum zoom level"),
        sa.Column('max_zoom', sa.Integer, nullable=True, default=22, comment="Maximum zoom level"),

        # Status and processing
        sa.Column('processing_status', sa.String(50), nullable=False, default='pending', comment="Status: pending, processing, ready, error"),
        sa.Column('error_message', sa.Text, nullable=True, comment="Error message if processing failed"),

        # Audit fields
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False),
        sa.Column('created_by', sa.String(255), nullable=True, comment="User who uploaded the layer"),

        # Additional metadata
        sa.Column('metadata_info', JSONB, nullable=True, comment="Additional layer metadata and attributes info"),
    )

    # Create additional indexes (id and layer_name indexes are created automatically)
    op.create_index('ix_spatial_layers_processing_status', 'spatial_layers', ['processing_status'])
    op.create_index('ix_spatial_layers_created_at', 'spatial_layers', ['created_at'])


def downgrade() -> None:
    """Drop spatial_layers table"""
    op.drop_table('spatial_layers')