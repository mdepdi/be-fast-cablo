"""
Pydantic models for FastAPI LastMile application
"""
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field
from enum import Enum

class ProcessingStatus(str, Enum):
    """Processing status enum"""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"

class LastMileRequest(BaseModel):
    """Request model for lastmile processing with file paths"""
    input_file_path: str = Field(..., description="Path to input CSV file containing lastmile requests")
    graph_path: str = Field(..., description="Path to GraphML file (e.g., sulawesi_graph.graphml)")
    fo_path: str = Field(..., description="Path to fiber optic shapefile directory")
    pop_path: str = Field(..., description="Path to population CSV file")

    # Column mapping
    lat_fe_column: str = Field(..., description="Column name for Far End latitude")
    lon_fe_column: str = Field(..., description="Column name for Far End longitude")
    lat_ne_column: str = Field(..., description="Column name for Near End latitude")
    lon_ne_column: str = Field(..., description="Column name for Near End longitude")
    fe_name_column: str = Field(..., description="Column name for Far End name")
    ne_name_column: str = Field(..., description="Column name for Near End name")

    # Optional parameters
    output_folder: str = Field("output", description="Output folder path")
    pulau: Optional[str] = Field("Sulawesi", description="Island name")
    ors_base_url: Optional[str] = Field("http://localhost:6080", description="ORS base URL")

class ProcessingResponse(BaseModel):
    """Response model for processing results"""
    request_id: str = Field(..., description="Unique request identifier")
    status: ProcessingStatus = Field(..., description="Processing status")
    message: str = Field(..., description="Status message")
    analysis_summary: Optional[Dict[str, Any]] = Field(None, description="Analysis summary")
    error_details: Optional[str] = Field(None, description="Error details if failed")
    database_id: Optional[str] = Field(None, description="Database record ID if saved to database")
    download_links: Optional[Dict[str, str]] = Field(None, description="Download URLs for output files")

class FileInfo(BaseModel):
    """File information model"""
    filename: str = Field(..., description="File name")
    size_bytes: int = Field(..., description="File size in bytes")
    columns: List[str] = Field(..., description="Available columns in CSV")

class CSVPreviewResponse(BaseModel):
    """CSV preview response model"""
    file_info: FileInfo = Field(..., description="File information")
    preview_data: List[Dict[str, Any]] = Field(..., description="Preview of first 5 rows")
    total_rows: int = Field(..., description="Total number of rows")

class HealthCheckResponse(BaseModel):
    """Health check response model"""
    status: str = Field(..., description="Service status")
    version: str = Field(..., description="API version")
    timestamp: str = Field(..., description="Current timestamp")
    dependencies: Dict[str, str] = Field(..., description="Dependency status")

class ErrorResponse(BaseModel):
    """Error response model"""
    error: str = Field(..., description="Error type")
    message: str = Field(..., description="Error message")
    details: Optional[str] = Field(None, description="Additional error details")