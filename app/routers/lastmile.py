"""
LastMile API Router
"""
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, status
from fastapi.responses import FileResponse
from typing import Dict, Any, Optional, List
import os
import uuid
from datetime import datetime
from urllib.parse import quote

from app.auth import verify_api_key
from app.models import ProcessingResponse, CSVPreviewResponse, ProcessingStatus, LastMileRequest
from app.utils import (
    validate_file_size, validate_csv_file, save_uploaded_file,
    get_csv_info, validate_column_mapping, cleanup_temp_file,
    create_output_directory, check_ors_connection
)
from app.core.lastmile_processor import processor
from app.config import settings

# Database imports
from app.database.config import SessionLocal
from app.database.utils import (
    create_processing_job,
    save_processing_results,
    mark_processing_failed,
    geodataframe_to_geojson
)
from app.database.schemas import ProcessingStatus as DBProcessingStatus
import geopandas as gpd

router = APIRouter(prefix="/api/v1/lastmile", tags=["LastMile Processing"])

def create_download_links(output_files: List[str], request_id: str) -> Dict[str, str]:
    """
    Create download links for output files

    Args:
        output_files: List of output file paths
        request_id: Request ID for the processing job

    Returns:
        Dictionary mapping file types to download URLs
    """
    download_links = {}
    # Use full base URL from settings
    base_url = f"{settings.BASE_URL}/api/v1/lastmile/download"

    for file_path in output_files:
        filename = os.path.basename(file_path)
        encoded_filename = quote(filename)

        # Determine file type based on filename
        if "detailed" in filename and filename.endswith(".parquet"):
            download_links["detailed_parquet"] = f"{base_url}/{request_id}/{encoded_filename}"
        elif "dissolved" in filename and filename.endswith(".parquet"):
            download_links["dissolved_parquet"] = f"{base_url}/{request_id}/{encoded_filename}"
        elif "dissolved" in filename and filename.endswith(".gpkg"):
            download_links["dissolved_geopackage"] = f"{base_url}/{request_id}/{encoded_filename}"
        elif "summary" in filename and filename.endswith(".csv"):
            download_links["summary_csv"] = f"{base_url}/{request_id}/{encoded_filename}"
        elif "routes" in filename and filename.endswith(".kml"):
            download_links["routes_kml"] = f"{base_url}/{request_id}/{encoded_filename}"
        elif "analysis_summary" in filename and filename.endswith(".json"):
            download_links["analysis_json"] = f"{base_url}/{request_id}/{encoded_filename}"

    return download_links

@router.post("/process", response_model=ProcessingResponse)
def post_last_mile_request(
    file: UploadFile = File(..., description="CSV file containing lastmile requests"),
    lat_fe_column: str = Form(..., description="Column name for Far End latitude"),
    lon_fe_column: str = Form(..., description="Column name for Far End longitude"),
    lat_ne_column: str = Form(..., description="Column name for Near End latitude"),
    lon_ne_column: str = Form(..., description="Column name for Near End longitude"),
    fe_name_column: str = Form(..., description="Column name for Far End name"),
    ne_name_column: str = Form(..., description="Column name for Near End name"),
    output_folder: str = Form(..., description="Output folder path"),
    pulau: Optional[str] = Form("Sulawesi", description="Island name"),
    graph_path: Optional[str] = Form(None, description="Path to GraphML file"),
    fo_path: Optional[str] = Form(None, description="Path to fiber optic shapefile"),
    pop_path: Optional[str] = Form(None, description="Path to population CSV file"),
    ors_base_url: Optional[str] = Form("http://localhost:6080", description="ORS base URL"),
    save_to_database: Optional[bool] = Form(True, description="Save results to database"),
    api_key: str = Depends(verify_api_key)
):
    """
    Process lastmile routing requests from uploaded CSV file

    This endpoint processes a CSV file containing lastmile routing requests.
    The CSV should contain columns for Far End and Near End coordinates and names.

    Parameters:
    - file: CSV file with lastmile requests
    - lat_fe_column: Column name containing Far End latitude
    - lon_fe_column: Column name containing Far End longitude
    - lat_ne_column: Column name containing Near End latitude
    - lon_ne_column: Column name containing Near End longitude
    - fe_name_column: Column name containing Far End name/identifier
    - ne_name_column: Column name containing Near End name/identifier
    - output_folder: Path where output files will be saved
    - pulau: Island name (default: Sulawesi)
    - graph_path: Optional path to GraphML file
    - fo_path: Optional path to fiber optic shapefile
    - pop_path: Optional path to population CSV file
    - ors_base_url: OpenRouteService base URL (default: http://localhost:6080)
    - save_to_database: Whether to save results to database (default: True)

    Returns:
    - ProcessingResponse with request ID, status, and analysis summary
    """

    request_id = str(uuid.uuid4())
    db_job = None
    db = None

    try:
                # Validate file first
        validate_csv_file(file)
        validate_file_size(file)

        # Save uploaded file
        input_file_path = save_uploaded_file(file, settings.UPLOAD_DIR)

        # Initialize database session if saving to database
        if save_to_database:
            db = SessionLocal()

            # Get CSV info for database record (now we have the file path)
            csv_info = get_csv_info(input_file_path)

            # Create processing job in database
            db_job = create_processing_job(
                db=db,
                request_id=request_id,
                input_filename=file.filename,
                total_requests=csv_info.get('total_rows', 0),
                pulau=pulau,
                ors_base_url=ors_base_url,
                graph_path=graph_path or settings.DEFAULT_GRAPH_PATH,
                created_by="api_user",  # You can modify this to get actual user info
                metadata_info={
                    "column_mapping": {
                        'lat_fe_column': lat_fe_column,
                        'lon_fe_column': lon_fe_column,
                        'lat_ne_column': lat_ne_column,
                        'lon_ne_column': lon_ne_column,
                        'fe_name_column': fe_name_column,
                        'ne_name_column': ne_name_column
                    },
                    "fo_path": fo_path,
                    "pop_path": pop_path,
                    "output_folder": output_folder
                }
            )
            print(f"📊 Created database job: {db_job.id}")

        try:
            # Create column mapping
            column_mapping = {
                'lat_fe_column': lat_fe_column,
                'lon_fe_column': lon_fe_column,
                'lat_ne_column': lat_ne_column,
                'lon_ne_column': lon_ne_column,
                'fe_name_column': fe_name_column,
                'ne_name_column': ne_name_column
            }

            # Validate column mapping
            validate_column_mapping(input_file_path, column_mapping)

            # Create output directory
            if not os.path.isabs(output_folder):
                output_folder = os.path.join(settings.OUTPUT_DIR, output_folder)

            output_dir = create_output_directory(output_folder, request_id)

            # Set default paths if not provided
            if not graph_path:
                graph_path = settings.DEFAULT_GRAPH_PATH
            if not fo_path:
                fo_path = settings.DEFAULT_FO_PATH
            if not pop_path:
                pop_path = settings.DEFAULT_POP_PATH

            # Check ORS connection (optional warning)
            if not check_ors_connection(ors_base_url):
                print(f"Warning: Could not connect to ORS server at {ors_base_url}")

            # Update database status to processing
            if save_to_database and db_job:
                from app.database.crud import processing_result_crud
                processing_result_crud.update_status(
                    db, db_job.id, DBProcessingStatus.PROCESSING
                )

            # Process the data
            result = processor.process_csv_data(
                input_file_path=input_file_path,
                column_mapping=column_mapping,
                output_folder=output_dir,
                pulau=pulau,
                graph_path=graph_path,
                fo_base_path=fo_path,
                pop_path=pop_path,
                ors_base_url=ors_base_url
            )

            if result["success"]:
                # Create download links using internal output files
                output_files = result.get("_output_files", [])
                download_links = create_download_links(output_files, request_id)

                # Save results to database if requested
                if save_to_database and db_job:
                    try:
                        # Load the dissolved GeoDataFrame from the saved file
                        dissolved_file = None
                        for file_path in output_files:
                            if "dissolved" in file_path and file_path.endswith(".parquet"):
                                dissolved_file = file_path
                                break

                        if dissolved_file and os.path.exists(dissolved_file):
                            dissolved_gdf = gpd.read_parquet(dissolved_file)

                            # Save to database
                            db_success = save_processing_results(
                                db=db,
                                processing_result_id=db_job.id,
                                dissolved_gdf=dissolved_gdf,
                                analysis_summary=result["analysis_summary"],
                                download_links=download_links
                            )

                            if db_success:
                                print(f"✅ Results saved to database successfully")
                            else:
                                print(f"⚠️ Failed to save results to database")
                        else:
                            print(f"⚠️ Could not find dissolved GeoDataFrame file for database storage")

                    except Exception as db_error:
                        print(f"⚠️ Database save error: {str(db_error)}")
                        # Don't fail the entire request if database save fails
                        if db_job:
                            mark_processing_failed(
                                db, db_job.id,
                                f"Processing succeeded but database save failed: {str(db_error)}"
                            )

                return ProcessingResponse(
                    request_id=request_id,
                    status=ProcessingStatus.COMPLETED,
                    message=result["message"],
                    analysis_summary=result["analysis_summary"],
                    database_id=str(db_job.id) if db_job else None,
                    download_links=download_links
                )
            else:
                # Mark as failed in database
                if save_to_database and db_job:
                    mark_processing_failed(
                        db, db_job.id, result["message"]
                    )

                return ProcessingResponse(
                    request_id=request_id,
                    status=ProcessingStatus.FAILED,
                    message=result["message"],
                    error_details=result.get("message"),
                    database_id=str(db_job.id) if db_job else None
                )

        finally:
            # Clean up uploaded file
            cleanup_temp_file(input_file_path)

    except HTTPException:
        # Mark as failed in database if there was a database job
        if save_to_database and db_job and db:
            mark_processing_failed(
                db, db_job.id, "HTTP error during processing"
            )
        raise
    except Exception as e:
        error_msg = f"Error processing lastmile request: {str(e)}"
        print(error_msg)

        # Mark as failed in database
        if save_to_database and db_job and db:
            mark_processing_failed(
                db, db_job.id, error_msg, {"traceback": str(e)}
            )

        return ProcessingResponse(
            request_id=request_id,
            status=ProcessingStatus.FAILED,
            message="Processing failed due to internal error",
            error_details=error_msg,
            database_id=str(db_job.id) if db_job else None
        )
    finally:
        # Close database session
        if db:
            db.close()

@router.get("/results/{database_id}")
def get_processing_result(database_id: str, api_key: str = Depends(verify_api_key)):
    """
    Get processing result from database by ID

    Parameters:
    - database_id: Database record ID

    Returns:
    - Processing result with GeoJSON data
    """
    try:
        import uuid
        from app.database.crud import processing_result_crud
        from app.database.utils import get_processing_result_geojson

        db = SessionLocal()
        try:
            # Convert string to UUID
            result_uuid = uuid.UUID(database_id)

            # Get processing result
            result = processing_result_crud.get(db, result_uuid)
            if not result:
                raise HTTPException(
                    status_code=404,
                    detail=f"Processing result not found for ID: {database_id}"
                )

            # Get GeoJSON data
            geojson_data = get_processing_result_geojson(db, result_uuid)

            return {
                "database_id": str(result.id),
                "request_id": result.request_id,
                "status": result.processing_status,
                "created_at": result.created_at.isoformat(),
                "completed_at": result.processing_completed_at.isoformat() if result.processing_completed_at else None,
                "duration_seconds": result.processing_duration_seconds,
                "input_filename": result.input_filename,
                "total_requests": result.total_requests,
                "processed_requests": result.processed_requests,
                "pulau": result.pulau,
                "result_analysis": geojson_data,
                "summary_analysis": result.summary_analysis,
                "error_message": result.error_message,
                "metadata_info": result.metadata_info
            }

        finally:
            db.close()

    except ValueError:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid database ID format: {database_id}"
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error retrieving processing result: {str(e)}"
        )


@router.get("/results")
def list_processing_results(
    status: Optional[str] = None,
    pulau: Optional[str] = None,
    limit: int = 10,
    offset: int = 0,
    api_key: str = Depends(verify_api_key)
):
    """
    List processing results with optional filtering

    Parameters:
    - status: Filter by processing status (pending, processing, completed, failed)
    - pulau: Filter by island name
    - limit: Maximum number of results (default: 10, max: 100)
    - offset: Number of results to skip (default: 0)

    Returns:
    - List of processing results
    """
    try:
        from app.database.crud import processing_result_crud
        from app.database.schemas import ProcessingResultQuery, ProcessingStatus as DBProcessingStatus

        # Validate limit
        if limit > 100:
            limit = 100

        # Create query parameters
        query_params = ProcessingResultQuery(
            status=DBProcessingStatus(status) if status else None,
            pulau=pulau,
            limit=limit,
            offset=offset
        )

        db = SessionLocal()
        try:
            # Get results
            results = processing_result_crud.get_multi(db, offset, limit, query_params)
            total_count = processing_result_crud.get_count(db, query_params)

            # Format response
            formatted_results = []
            for result in results:
                formatted_results.append({
                    "database_id": str(result.id),
                    "request_id": result.request_id,
                    "status": result.processing_status,
                    "created_at": result.created_at.isoformat(),
                    "completed_at": result.processing_completed_at.isoformat() if result.processing_completed_at else None,
                    "duration_seconds": result.processing_duration_seconds,
                    "input_filename": result.input_filename,
                    "total_requests": result.total_requests,
                    "processed_requests": result.processed_requests,
                    "pulau": result.pulau,
                    "has_results": result.result_analysis is not None,
                    "error_message": result.error_message
                })

            return {
                "results": formatted_results,
                "total_count": total_count,
                "limit": limit,
                "offset": offset,
                "has_next": offset + limit < total_count,
                "has_prev": offset > 0
            }

        finally:
            db.close()

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error listing processing results: {str(e)}"
        )


@router.get("/results/{database_id}/geojson")
def get_processing_result_geojson_endpoint(database_id: str, api_key: str = Depends(verify_api_key)):
    """
    Get processing result as GeoJSON

    Parameters:
    - database_id: Database record ID

    Returns:
    - GeoJSON FeatureCollection
    """
    try:
        import uuid
        from app.database.utils import get_processing_result_geojson

        db = SessionLocal()
        try:
            # Convert string to UUID
            result_uuid = uuid.UUID(database_id)

            # Get GeoJSON data
            geojson_data = get_processing_result_geojson(db, result_uuid)

            if not geojson_data:
                raise HTTPException(
                    status_code=404,
                    detail=f"No GeoJSON data found for ID: {database_id}"
                )

            return geojson_data

        finally:
            db.close()

    except ValueError:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid database ID format: {database_id}"
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error retrieving GeoJSON data: {str(e)}"
        )


@router.get("/stats")
def get_processing_stats(api_key: str = Depends(verify_api_key)):
    """
    Get processing statistics

    Returns:
    - Summary statistics of all processing jobs
    """
    try:
        from app.database.crud import processing_result_crud

        db = SessionLocal()
        try:
            stats = processing_result_crud.get_summary_stats(db)
            return stats

        finally:
            db.close()

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error retrieving processing stats: {str(e)}"
        )


@router.get("/health")
def health_check():
    """
    Health check endpoint
    """
    try:
        ors_status = "connected" if check_ors_connection(settings.ORS_BASE_URL) else "disconnected"

        # Check database connection
        db_status = "disconnected"
        try:
            db = SessionLocal()
            from sqlalchemy import text
            db.execute(text("SELECT 1"))
            db_status = "connected"
            db.close()
        except Exception:
            pass

        return {
            "status": "healthy",
            "version": settings.API_VERSION,
            "timestamp": datetime.now().isoformat(),
            "dependencies": {
                "ors_server": ors_status,
                "database": db_status
            }
        }
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Health check failed: {str(e)}"
        )

@router.get("/download/{request_id}/{filename}")
def download_file(
    request_id: str,
    filename: str
):
    """
    Download output file by request ID and filename

    Parameters:
    - request_id: Request ID from processing
    - filename: Name of the file to download

    Returns:
    - File download response
    """
    try:
        # Construct file path
        # Files are stored in: outputs/{output_folder}/request_{request_id}/{filename}
        # We need to find the file in the outputs directory structure

        # Search in outputs directory
        outputs_base = settings.OUTPUT_DIR

        # Try different possible paths
        possible_paths = [
            # Direct path in request folder
            os.path.join(outputs_base, f"request_{request_id}", filename),
            # Path with output subfolder
            os.path.join(outputs_base, "output", f"request_{request_id}", filename),
            # Path with outputs subfolder
            os.path.join(outputs_base, "outputs", "output", f"request_{request_id}", filename),
        ]

        file_path = None
        for path in possible_paths:
            if os.path.exists(path):
                file_path = path
                break

        if not file_path:
            # Try to find the file by searching recursively
            for root, dirs, files in os.walk(outputs_base):
                if filename in files and request_id in root:
                    file_path = os.path.join(root, filename)
                    break

        if not file_path or not os.path.exists(file_path):
            raise HTTPException(
                status_code=404,
                detail=f"File not found: {filename} for request {request_id}"
            )

        # Determine media type based on file extension
        media_type_map = {
            '.parquet': 'application/octet-stream',
            '.gpkg': 'application/geopackage+sqlite3',
            '.csv': 'text/csv',
            '.kml': 'application/vnd.google-earth.kml+xml',
            '.json': 'application/json',
            '.geojson': 'application/geo+json'
        }

        file_ext = os.path.splitext(filename)[1].lower()
        media_type = media_type_map.get(file_ext, 'application/octet-stream')

        return FileResponse(
            path=file_path,
            filename=filename,
            media_type=media_type
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error downloading file: {str(e)}"
        )

@router.get("/download/{request_id}")
def list_downloadable_files(
    request_id: str
):
    """
    List all downloadable files for a request ID

    Parameters:
    - request_id: Request ID from processing

    Returns:
    - List of available files with download links
    """
    try:
        # Search for files in outputs directory
        outputs_base = settings.OUTPUT_DIR
        files_found = []

        # Search recursively for files related to this request
        for root, dirs, files in os.walk(outputs_base):
            if request_id in root:
                for file in files:
                    file_path = os.path.join(root, file)
                    file_size = os.path.getsize(file_path)

                    files_found.append({
                        "filename": file,
                        "size_bytes": file_size,
                        "download_url": f"{settings.BASE_URL}/api/v1/lastmile/download/{request_id}/{quote(file)}",
                        "file_type": os.path.splitext(file)[1].lower()
                    })

        if not files_found:
            raise HTTPException(
                status_code=404,
                detail=f"No files found for request {request_id}"
            )

        return {
            "request_id": request_id,
            "files": files_found,
            "total_files": len(files_found)
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error listing files: {str(e)}"
        )