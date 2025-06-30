"""
Pydantic Schemas for LastMile Processing
"""

from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, List, Dict, Any
from datetime import datetime
from uuid import UUID
from enum import Enum


class ProcessingStatus(str, Enum):
    """Processing status enumeration"""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class LayerProcessingStatus(str, Enum):
    """Layer processing status enumeration"""
    PENDING = "pending"
    PROCESSING = "processing"
    READY = "ready"
    ERROR = "error"


class LayerFileType(str, Enum):
    """Supported file types for spatial layers"""
    PARQUET = "parquet"
    GEOPARQUET = "geoparquet"
    GEOJSON = "geojson"
    SHAPEFILE = "shapefile"


# Base schemas
class LastMileProcessingResultBase(BaseModel):
    """Base schema for LastMile Processing Result"""
    request_id: str = Field(..., description="Unique request identifier")
    input_filename: Optional[str] = Field(None, description="Original input file name")
    total_requests: Optional[int] = Field(None, description="Total number of requests processed")
    processed_requests: Optional[int] = Field(None, description="Number of successfully processed requests")
    processing_status: ProcessingStatus = Field(ProcessingStatus.PENDING, description="Processing status")
    pulau: Optional[str] = Field(None, description="Island name used for processing")
    ors_base_url: Optional[str] = Field(None, description="ORS server URL used")
    graph_path: Optional[str] = Field(None, description="Path to graph file used")
    result_analysis: Optional[Dict[str, Any]] = Field(None, description="Complete geodataframe results as GeoJSON")
    summary_analysis: Optional[Dict[str, Any]] = Field(None, description="Summary statistics and analysis")
    download_links: Optional[Dict[str, str]] = Field(None, description="Download URLs for output files")
    error_message: Optional[str] = Field(None, description="Error message if processing failed")
    error_details: Optional[Dict[str, Any]] = Field(None, description="Detailed error information")
    created_by: Optional[str] = Field(None, description="User or system that created this record")
    metadata_info: Optional[Dict[str, Any]] = Field(None, description="Additional metadata and configuration")


class LastMileProcessingResultCreate(LastMileProcessingResultBase):
    """Schema for creating a new processing result"""
    pass


class LastMileProcessingResultUpdate(BaseModel):
    """Schema for updating a processing result"""
    processing_status: Optional[ProcessingStatus] = None
    processing_completed_at: Optional[datetime] = None
    processing_duration_seconds: Optional[int] = None
    result_analysis: Optional[Dict[str, Any]] = None
    summary_analysis: Optional[Dict[str, Any]] = None
    download_links: Optional[Dict[str, str]] = None
    error_message: Optional[str] = None
    error_details: Optional[Dict[str, Any]] = None
    processed_requests: Optional[int] = None


class LastMileProcessingResultResponse(LastMileProcessingResultBase):
    """Schema for response with all fields"""
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    processing_started_at: Optional[datetime] = None
    processing_completed_at: Optional[datetime] = None
    processing_duration_seconds: Optional[int] = None
    created_at: datetime
    updated_at: datetime


# Request details are now stored in summary_analysis JSONB column
# No separate table needed


# Composite schemas for complex operations
class ProcessingJobRequest(BaseModel):
    """Schema for submitting a new processing job"""
    input_file_path: str = Field(..., description="Path to input CSV file")
    pulau: str = Field("Sulawesi", description="Island name")
    graph_path: str = Field("./data/sulawesi_graph.graphml", description="Path to graph file")
    ors_base_url: str = Field("http://localhost:6080", description="ORS server URL")
    output_folder: str = Field("output", description="Output folder path")
    created_by: Optional[str] = Field(None, description="User submitting the job")
    metadata_info: Optional[Dict[str, Any]] = Field(None, description="Additional job metadata")


class ProcessingJobResponse(BaseModel):
    """Schema for processing job response"""
    success: bool
    request_id: str
    message: str
    processing_result_id: Optional[UUID] = None
    estimated_duration_minutes: Optional[int] = None


class ProcessingSummary(BaseModel):
    """Schema for processing summary statistics"""
    total_jobs: int
    pending_jobs: int
    processing_jobs: int
    completed_jobs: int
    failed_jobs: int
    total_requests_processed: int
    total_distance_km: float
    average_processing_time_minutes: Optional[float] = None


class GeoJSONFeature(BaseModel):
    """Schema for GeoJSON feature"""
    type: str = Field("Feature", description="GeoJSON type")
    geometry: Dict[str, Any] = Field(..., description="GeoJSON geometry")
    properties: Dict[str, Any] = Field(..., description="Feature properties")


class GeoJSONFeatureCollection(BaseModel):
    """Schema for GeoJSON feature collection"""
    type: str = Field("FeatureCollection", description="GeoJSON type")
    features: List[GeoJSONFeature] = Field(..., description="List of features")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Collection metadata")


# Query schemas
class ProcessingResultQuery(BaseModel):
    """Schema for querying processing results"""
    status: Optional[ProcessingStatus] = None
    created_by: Optional[str] = None
    pulau: Optional[str] = None
    date_from: Optional[datetime] = None
    date_to: Optional[datetime] = None
    limit: int = Field(100, ge=1, le=1000)
    offset: int = Field(0, ge=0)


class ProcessingResultList(BaseModel):
    """Schema for paginated list of processing results"""
    results: List[LastMileProcessingResultResponse]
    total_count: int
    limit: int
    offset: int
    has_next: bool
    has_prev: bool


# Spatial Layer Schemas
class SpatialLayerBase(BaseModel):
    """Base schema for Spatial Layer"""
    layer_name: str = Field(..., description="Unique layer name (also table name)", min_length=1, max_length=255)
    display_name: str = Field(..., description="Human-readable display name", min_length=1, max_length=255)
    description: Optional[str] = Field(None, description="Layer description")
    file_type: LayerFileType = Field(..., description="File type")
    geometry_type: Optional[str] = Field(None, description="Geometry type: Point, LineString, Polygon, etc.")
    srid: int = Field(4326, description="Spatial Reference System Identifier")
    bbox: Optional[List[float]] = Field(None, description="Bounding box coordinates [minx, miny, maxx, maxy]")
    maplibre_style: Dict[str, Any] = Field(default_factory=dict, description="MapLibre GL style specification")
    default_visibility: bool = Field(True, description="Default visibility state")
    min_zoom: Optional[int] = Field(0, ge=0, le=24, description="Minimum zoom level")
    max_zoom: Optional[int] = Field(22, ge=0, le=24, description="Maximum zoom level")
    created_by: Optional[str] = Field(None, description="User who uploaded the layer")
    metadata_info: Optional[Dict[str, Any]] = Field(None, description="Additional layer metadata")


class SpatialLayerCreate(SpatialLayerBase):
    """Schema for creating a new spatial layer"""
    original_filename: str = Field(..., description="Original uploaded file name")
    file_size_bytes: Optional[int] = Field(None, description="File size in bytes")


class SpatialLayerUpdate(BaseModel):
    """Schema for updating a spatial layer"""
    display_name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None
    maplibre_style: Optional[Dict[str, Any]] = None
    default_visibility: Optional[bool] = None
    min_zoom: Optional[int] = Field(None, ge=0, le=24)
    max_zoom: Optional[int] = Field(None, ge=0, le=24)
    processing_status: Optional[LayerProcessingStatus] = None
    error_message: Optional[str] = None
    martin_layer_id: Optional[str] = None
    martin_url: Optional[str] = None
    feature_count: Optional[int] = None
    bbox: Optional[List[float]] = None
    geometry_type: Optional[str] = None
    metadata_info: Optional[Dict[str, Any]] = None


class SpatialLayerResponse(SpatialLayerBase):
    """Schema for spatial layer response"""
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    original_filename: str
    file_size_bytes: Optional[int] = None
    feature_count: Optional[int] = None
    martin_layer_id: Optional[str] = None
    martin_url: Optional[str] = None
    processing_status: LayerProcessingStatus
    error_message: Optional[str] = None
    created_at: datetime
    updated_at: datetime


class SpatialLayerListItem(BaseModel):
    """Schema for spatial layer list item (minimal info)"""
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    layer_name: str
    display_name: str
    geometry_type: Optional[str] = None
    feature_count: Optional[int] = None
    processing_status: LayerProcessingStatus
    default_visibility: bool
    created_at: datetime


class FileUploadRequest(BaseModel):
    """Schema for file upload request"""
    display_name: str = Field(..., description="Human-readable display name")
    description: Optional[str] = Field(None, description="Layer description")
    srid: int = Field(4326, description="Target SRID for the layer")
    maplibre_style: Optional[Dict[str, Any]] = Field(None, description="Initial MapLibre style")


class FileUploadResponse(BaseModel):
    """Schema for file upload response"""
    success: bool
    message: str
    layer_id: Optional[UUID] = None
    layer_name: Optional[str] = None
    processing_status: Optional[LayerProcessingStatus] = None