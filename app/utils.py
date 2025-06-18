"""
Utility functions for FastAPI LastMile application
"""
import os
import pandas as pd
from typing import List, Dict, Any, Optional
from fastapi import HTTPException, UploadFile
import tempfile
import uuid
from app.config import settings

def validate_file_size(file: UploadFile) -> None:
    """
    Validate uploaded file size

    Args:
        file: Uploaded file

    Raises:
        HTTPException: If file is too large
    """
    if hasattr(file.file, 'seek'):
        # Get file size
        file.file.seek(0, 2)  # Seek to end
        file_size = file.file.tell()
        file.file.seek(0)  # Reset to beginning

        if file_size > settings.MAX_FILE_SIZE_BYTES:
            raise HTTPException(
                status_code=413,
                detail=f"File too large. Maximum size: {settings.MAX_FILE_SIZE_MB}MB"
            )

def validate_csv_file(file: UploadFile) -> None:
    """
    Validate if uploaded file is a CSV

    Args:
        file: Uploaded file

    Raises:
        HTTPException: If file is not a CSV
    """
    if not file.filename.lower().endswith('.csv'):
        raise HTTPException(
            status_code=400,
            detail="Only CSV files are allowed"
        )

def save_uploaded_file(file: UploadFile, directory: str) -> str:
    """
    Save uploaded file to specified directory

    Args:
        file: Uploaded file
        directory: Target directory

    Returns:
        str: Path of saved file
    """
    # Generate unique filename
    file_id = str(uuid.uuid4())
    filename = f"{file_id}_{file.filename}"
    file_path = os.path.join(directory, filename)

    # Ensure directory exists
    os.makedirs(directory, exist_ok=True)

    # Save file
    with open(file_path, "wb") as buffer:
        content = file.file.read()
        buffer.write(content)

    return file_path

def get_csv_info(file_path: str) -> Dict[str, Any]:
    """
    Get information about CSV file

    Args:
        file_path: Path to CSV file

    Returns:
        Dict containing file info and preview
    """
    try:
        # Read CSV
        df = pd.read_csv(file_path)

        # Get file size
        file_size = os.path.getsize(file_path)

        # Get preview data (first 5 rows)
        preview_data = df.head(5).to_dict('records')

        return {
            "filename": os.path.basename(file_path),
            "size_bytes": file_size,
            "columns": df.columns.tolist(),
            "total_rows": len(df),
            "preview_data": preview_data
        }

    except Exception as e:
        raise HTTPException(
            status_code=400,
            detail=f"Error reading CSV file: {str(e)}"
        )

def validate_column_mapping(file_path: str, column_mapping: Dict[str, str]) -> None:
    """
    Validate if specified columns exist in CSV

    Args:
        file_path: Path to CSV file
        column_mapping: Dictionary mapping column names

    Raises:
        HTTPException: If required columns are missing
    """
    try:
        df = pd.read_csv(file_path, nrows=1)  # Read only first row to get columns
        available_columns = df.columns.tolist()

        required_fields = [
            'lat_fe_column', 'lon_fe_column',
            'lat_ne_column', 'lon_ne_column',
            'fe_name_column', 'ne_name_column'
        ]

        missing_columns = []
        for field in required_fields:
            column_name = column_mapping.get(field)
            if not column_name:
                missing_columns.append(f"{field} mapping")
            elif column_name not in available_columns:
                missing_columns.append(f"Column '{column_name}' (for {field})")

        if missing_columns:
            raise HTTPException(
                status_code=400,
                detail=f"Missing required columns: {', '.join(missing_columns)}"
            )

    except pd.errors.EmptyDataError:
        raise HTTPException(
            status_code=400,
            detail="CSV file is empty"
        )
    except Exception as e:
        raise HTTPException(
            status_code=400,
            detail=f"Error validating CSV columns: {str(e)}"
        )

def cleanup_temp_file(file_path: str) -> None:
    """
    Clean up temporary file

    Args:
        file_path: Path to file to delete
    """
    try:
        if os.path.exists(file_path):
            os.remove(file_path)
    except Exception as e:
        print(f"Warning: Could not delete temporary file {file_path}: {str(e)}")

def create_output_directory(base_path: str, request_id: str) -> str:
    """
    Create output directory for request

    Args:
        base_path: Base output directory
        request_id: Unique request identifier

    Returns:
        str: Path to created directory
    """
    output_dir = os.path.join(base_path, f"request_{request_id}")
    os.makedirs(output_dir, exist_ok=True)
    return output_dir

def check_ors_connection(ors_base_url: str) -> bool:
    """
    Check if ORS server is accessible

    Args:
        ors_base_url: ORS base URL

    Returns:
        bool: True if accessible, False otherwise
    """
    try:
        import requests
        health_url = f"{ors_base_url}/ors/v2/health"
        response = requests.get(health_url, timeout=5)
        return response.status_code == 200
    except Exception:
        return False