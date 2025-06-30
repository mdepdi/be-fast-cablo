"""
SQLAlchemy Models for LastMile Processing
"""

from sqlalchemy import Column, Integer, String, DateTime, Text, Boolean
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.sql import func
import uuid
from .config import Base


class LastMileProcessingResult(Base):
    """
    Table to store lastmile processing results
    """
    __tablename__ = "lastmile_processing_results"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    request_id = Column(String(255), nullable=False, index=True, comment="Unique request identifier")

    # Input information
    input_filename = Column(String(500), nullable=True, comment="Original input file name")
    total_requests = Column(Integer, nullable=True, comment="Total number of requests processed")
    processed_requests = Column(Integer, nullable=True, comment="Number of successfully processed requests")

    # Processing metadata
    processing_status = Column(String(50), nullable=False, default="pending", comment="Status: pending, processing, completed, failed")
    processing_started_at = Column(DateTime(timezone=True), nullable=True, comment="When processing started")
    processing_completed_at = Column(DateTime(timezone=True), nullable=True, comment="When processing completed")
    processing_duration_seconds = Column(Integer, nullable=True, comment="Total processing time in seconds")

    # Configuration used
    pulau = Column(String(100), nullable=True, comment="Island name used for processing")
    ors_base_url = Column(String(500), nullable=True, comment="ORS server URL used")
    graph_path = Column(String(500), nullable=True, comment="Path to graph file used")

    # Results - JSONB columns for analysis data
    result_analysis = Column(JSONB, nullable=True, comment="Complete geodataframe results as GeoJSON")
    summary_analysis = Column(JSONB, nullable=True, comment="Summary statistics and analysis")
    download_links = Column(JSONB, nullable=True, comment="Download URLs for output files as JSONB")

    # Error information
    error_message = Column(Text, nullable=True, comment="Error message if processing failed")
    error_details = Column(JSONB, nullable=True, comment="Detailed error information")

    # Audit fields
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    created_by = Column(String(255), nullable=True, comment="User or system that created this record")

    # Additional metadata
    metadata_info = Column(JSONB, nullable=True, comment="Additional metadata and configuration")

    def __repr__(self):
        return f"<LastMileProcessingResult(id={self.id}, request_id='{self.request_id}', status='{self.processing_status}')>"


class SpatialLayer(Base):
    """
    Table to store spatial layer metadata from uploaded files
    """
    __tablename__ = "spatial_layers"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    layer_name = Column(String(255), nullable=False, unique=True, index=True, comment="Unique layer name (also table name)")
    display_name = Column(String(255), nullable=False, comment="Human-readable display name")
    description = Column(Text, nullable=True, comment="Layer description")

    # File metadata
    original_filename = Column(String(500), nullable=False, comment="Original uploaded file name")
    file_type = Column(String(50), nullable=False, comment="File type: parquet, geoparquet, etc.")
    file_size_bytes = Column(Integer, nullable=True, comment="File size in bytes")

    # Spatial metadata
    geometry_type = Column(String(50), nullable=True, comment="Geometry type: Point, LineString, Polygon, etc.")
    srid = Column(Integer, nullable=False, default=4326, comment="Spatial Reference System Identifier")
    bbox = Column(JSONB, nullable=True, comment="Bounding box coordinates [minx, miny, maxx, maxy]")
    feature_count = Column(Integer, nullable=True, comment="Number of features in the layer")

    # Martin tile service
    martin_layer_id = Column(String(255), nullable=True, comment="Layer ID in Martin tile service")
    martin_url = Column(String(500), nullable=True, comment="Martin tile service URL for this layer")

    # MapLibre styling
    maplibre_style = Column(JSONB, nullable=False, default={}, comment="MapLibre GL style specification for this layer")
    default_visibility = Column(Boolean, nullable=False, default=True, comment="Default visibility state")
    min_zoom = Column(Integer, nullable=True, default=0, comment="Minimum zoom level")
    max_zoom = Column(Integer, nullable=True, default=22, comment="Maximum zoom level")

    # Status and processing
    processing_status = Column(String(50), nullable=False, default="pending", comment="Status: pending, processing, ready, error")
    error_message = Column(Text, nullable=True, comment="Error message if processing failed")

    # Audit fields
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    created_by = Column(String(255), nullable=True, comment="User who uploaded the layer")

    # Additional metadata
    metadata_info = Column(JSONB, nullable=True, comment="Additional layer metadata and attributes info")

    def __repr__(self):
        return f"<SpatialLayer(id={self.id}, layer_name='{self.layer_name}', status='{self.processing_status}')>"


