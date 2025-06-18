"""
Database Utility Functions for LastMile Processing
"""

import json
import geopandas as gpd
import pandas as pd
from typing import Dict, Any, Optional, List
from sqlalchemy.orm import Session
from datetime import datetime
import uuid

from .models import LastMileProcessingResult
from .schemas import (
    LastMileProcessingResultCreate,
    ProcessingStatus
)
from .crud import processing_result_crud


def geodataframe_to_geojson(gdf: gpd.GeoDataFrame) -> Dict[str, Any]:
    """
    Convert GeoDataFrame to GeoJSON format for database storage

    Args:
        gdf: GeoDataFrame to convert

    Returns:
        Dict containing GeoJSON-formatted data
    """
    try:
        # Ensure CRS is WGS84 for GeoJSON
        if gdf.crs != 'EPSG:4326':
            gdf = gdf.to_crs('EPSG:4326')

        # Convert to GeoJSON
        geojson_dict = json.loads(gdf.to_json())

        # Add metadata
        geojson_dict['metadata'] = {
            'total_features': len(gdf),
            'columns': list(gdf.columns),
            'crs': 'EPSG:4326',
            'generated_at': datetime.utcnow().isoformat()
        }

        return geojson_dict

    except Exception as e:
        print(f"Error converting GeoDataFrame to GeoJSON: {str(e)}")
        return {
            'type': 'FeatureCollection',
            'features': [],
            'metadata': {
                'error': str(e),
                'generated_at': datetime.utcnow().isoformat()
            }
        }


def geojson_to_geodataframe(geojson_dict: Dict[str, Any]) -> gpd.GeoDataFrame:
    """
    Convert GeoJSON from database back to GeoDataFrame

    Args:
        geojson_dict: GeoJSON dictionary from database

    Returns:
        GeoDataFrame
    """
    try:
        # Create GeoDataFrame from GeoJSON
        gdf = gpd.GeoDataFrame.from_features(geojson_dict['features'])

        # Set CRS
        if 'metadata' in geojson_dict and 'crs' in geojson_dict['metadata']:
            gdf.set_crs(geojson_dict['metadata']['crs'], inplace=True)
        else:
            gdf.set_crs('EPSG:4326', inplace=True)

        return gdf

    except Exception as e:
        print(f"Error converting GeoJSON to GeoDataFrame: {str(e)}")
        return gpd.GeoDataFrame()


def create_processing_job(
    db: Session,
    request_id: str,
    input_filename: str,
    total_requests: int,
    pulau: str,
    ors_base_url: str,
    graph_path: str,
    created_by: Optional[str] = None,
    metadata_info: Optional[Dict[str, Any]] = None
) -> LastMileProcessingResult:
    """
    Create a new processing job in the database

    Args:
        db: Database session
        request_id: Unique request identifier
        input_filename: Input CSV filename
        total_requests: Total number of requests to process
        pulau: Island name
        ors_base_url: ORS server URL
        graph_path: Path to graph file
        created_by: User creating the job
        metadata_info: Additional metadata

    Returns:
        Created LastMileProcessingResult instance
    """
    job_data = LastMileProcessingResultCreate(
        request_id=request_id,
        input_filename=input_filename,
        total_requests=total_requests,
        processed_requests=0,
        processing_status=ProcessingStatus.PENDING,
        pulau=pulau,
        ors_base_url=ors_base_url,
        graph_path=graph_path,
        created_by=created_by,
        metadata_info=metadata_info or {}
    )

    return processing_result_crud.create(db, job_data)


def save_processing_results(
    db: Session,
    processing_result_id: uuid.UUID,
    dissolved_gdf: gpd.GeoDataFrame,
    analysis_summary: Dict[str, Any],
    download_links: Optional[Dict[str, str]] = None,
    individual_requests: Optional[List[Dict[str, Any]]] = None
) -> bool:
    """
    Save processing results to database

    Args:
        db: Database session
        processing_result_id: ID of the processing result record
        dissolved_gdf: Final dissolved GeoDataFrame
        analysis_summary: Analysis summary dictionary
        download_links: Dictionary of download URLs for output files
        individual_requests: List of individual request details

    Returns:
        Success boolean
    """
    try:
        # Convert GeoDataFrame to GeoJSON
        result_geojson = geodataframe_to_geojson(dissolved_gdf)

        # Update main processing result
        update_data = {
            'processing_status': ProcessingStatus.COMPLETED,
            'result_analysis': result_geojson,
            'summary_analysis': analysis_summary,
            'download_links': download_links,
            'processed_requests': analysis_summary.get('total_requests', 0)
        }

        processing_result_crud.update(db, processing_result_id, update_data)

        # Individual request details are now stored in summary_analysis
        # No need for separate table

        return True

    except Exception as e:
        print(f"Error saving processing results: {str(e)}")
        # Mark as failed
        processing_result_crud.update_status(
            db,
            processing_result_id,
            ProcessingStatus.FAILED,
            f"Error saving results: {str(e)}"
        )
        return False


def mark_processing_failed(
    db: Session,
    processing_result_id: uuid.UUID,
    error_message: str,
    error_details: Optional[Dict[str, Any]] = None
) -> bool:
    """
    Mark processing as failed with error details

    Args:
        db: Database session
        processing_result_id: ID of the processing result record
        error_message: Error message
        error_details: Detailed error information

    Returns:
        Success boolean
    """
    try:
        update_data = {
            'processing_status': ProcessingStatus.FAILED,
            'error_message': error_message,
            'error_details': error_details or {}
        }

        processing_result_crud.update(db, processing_result_id, update_data)
        return True

    except Exception as e:
        print(f"Error marking processing as failed: {str(e)}")
        return False


def get_processing_result_geojson(
    db: Session,
    processing_result_id: uuid.UUID
) -> Optional[Dict[str, Any]]:
    """
    Get processing result as GeoJSON

    Args:
        db: Database session
        processing_result_id: ID of the processing result record

    Returns:
        GeoJSON dictionary or None
    """
    try:
        result = processing_result_crud.get(db, processing_result_id)
        if result and result.result_analysis:
            return result.result_analysis
        return None

    except Exception as e:
        print(f"Error retrieving processing result GeoJSON: {str(e)}")
        return None


def get_processing_result_geodataframe(
    db: Session,
    processing_result_id: uuid.UUID
) -> Optional[gpd.GeoDataFrame]:
    """
    Get processing result as GeoDataFrame

    Args:
        db: Database session
        processing_result_id: ID of the processing result record

    Returns:
        GeoDataFrame or None
    """
    try:
        geojson_data = get_processing_result_geojson(db, processing_result_id)
        if geojson_data:
            return geojson_to_geodataframe(geojson_data)
        return None

    except Exception as e:
        print(f"Error retrieving processing result GeoDataFrame: {str(e)}")
        return None


def cleanup_old_processing_results(
    db: Session,
    days_old: int = 30,
    keep_successful: bool = True
) -> int:
    """
    Clean up old processing results

    Args:
        db: Database session
        days_old: Delete records older than this many days
        keep_successful: Whether to keep successful results

    Returns:
        Number of records deleted
    """
    try:
        from sqlalchemy import and_

        cutoff_date = datetime.utcnow() - pd.Timedelta(days=days_old)

        query = db.query(LastMileProcessingResult).filter(
            LastMileProcessingResult.created_at < cutoff_date
        )

        if keep_successful:
            query = query.filter(
                LastMileProcessingResult.processing_status != ProcessingStatus.COMPLETED
            )

        # Get IDs to delete
        records_to_delete = query.all()
        count = len(records_to_delete)

        # Request details are now stored in JSONB, no separate table to clean

        # Delete main records
        for record in records_to_delete:
            processing_result_crud.delete(db, record.id)

        return count

    except Exception as e:
        print(f"Error cleaning up old processing results: {str(e)}")
        return 0


def validate_geojson(geojson_dict: Dict[str, Any]) -> bool:
    """
    Validate GeoJSON structure

    Args:
        geojson_dict: GeoJSON dictionary to validate

    Returns:
        Validation result
    """
    try:
        required_fields = ['type', 'features']

        for field in required_fields:
            if field not in geojson_dict:
                return False

        if geojson_dict['type'] != 'FeatureCollection':
            return False

        if not isinstance(geojson_dict['features'], list):
            return False

        # Validate each feature
        for feature in geojson_dict['features']:
            if not isinstance(feature, dict):
                return False
            if 'type' not in feature or feature['type'] != 'Feature':
                return False
            if 'geometry' not in feature or 'properties' not in feature:
                return False

        return True

    except Exception:
        return False