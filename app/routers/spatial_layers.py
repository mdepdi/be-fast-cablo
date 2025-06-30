"""
API Router for Spatial Layer Management
"""

import os
import shutil
import uuid
from pathlib import Path
from typing import List, Optional
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from ..database.config import SessionLocal, get_db
from ..database.schemas import (
    SpatialLayerResponse,
    SpatialLayerListItem,
    SpatialLayerUpdate,
    FileUploadResponse,
    LayerProcessingStatus
)
from ..database.crud import spatial_layer_crud
from ..core.spatial_layer_processor import get_spatial_processor
# from ..auth import get_current_user  # TODO: Add when auth is implemented


router = APIRouter(
    prefix="/api/spatial-layers",
    tags=["Spatial Layers"],
    responses={404: {"description": "Not found"}},
)


UPLOAD_DIR = Path("uploads/spatial_layers")
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

ALLOWED_EXTENSIONS = {'.parquet', '.geoparquet', '.geojson', '.shp', '.zip'}


def save_upload_file(upload_file: UploadFile, destination: Path) -> None:
    """Save uploaded file to destination"""
    try:
        with destination.open("wb") as buffer:
            shutil.copyfileobj(upload_file.file, buffer)
    finally:
        upload_file.file.close()



@router.post("/upload", response_model=FileUploadResponse)
async def upload_spatial_file(
    file: UploadFile = File(...),
    display_name: str = Form(...),
    description: Optional[str] = Form(None),
    target_srid: int = Form(4326),
    # current_user = Depends(get_current_user)  # Uncomment when auth is ready
):
    """Upload and process spatial file synchronously (parquet, geoparquet, geojson, shapefile)"""

    # Validate file extension
    file_extension = Path(file.filename).suffix.lower()
    if file_extension not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"File type {file_extension} not supported. Allowed types: {', '.join(ALLOWED_EXTENSIONS)}"
        )

    # Generate unique filename
    file_id = uuid.uuid4().hex[:8]
    filename = f"{file_id}_{file.filename}"
    file_path = UPLOAD_DIR / filename

    try:
        # Save uploaded file
        save_upload_file(file, file_path)

        # Process the file immediately (synchronously)
        processor = get_spatial_processor()
        success, message, layer_id = await processor.process_upload(
            file_path=str(file_path),
            display_name=display_name,
            description=description,
            target_srid=target_srid,
            created_by=None  # current_user.username if current_user else None
        )

        # Clean up uploaded file after processing
        try:
            os.unlink(file_path)
        except:
            pass

        if success:
            return FileUploadResponse(
                success=True,
                message=f"File uploaded and processed successfully. {message}",
                processing_status=LayerProcessingStatus.READY,
                layer_id=layer_id
            )
        else:
            raise HTTPException(
                status_code=500,
                detail=f"Error processing file: {message}"
            )

    except Exception as e:
        # Clean up file if error occurs
        if file_path.exists():
            file_path.unlink()

        raise HTTPException(
            status_code=500,
            detail=f"Error uploading file: {str(e)}"
        )


@router.get("/", response_model=List[SpatialLayerListItem])
async def list_spatial_layers(
    skip: int = 0,
    limit: int = 100,
    status: Optional[LayerProcessingStatus] = None,
    db: Session = Depends(get_db)
):
    """Get list of spatial layers"""
    try:
        if status:
            layers = spatial_layer_crud.get_by_status(db, status)
        else:
            layers = spatial_layer_crud.get_all(db, skip=skip, limit=limit)

        return [
            SpatialLayerListItem(
                id=layer.id,
                layer_name=layer.layer_name,
                display_name=layer.display_name,
                geometry_type=layer.geometry_type,
                feature_count=layer.feature_count,
                processing_status=layer.processing_status,
                default_visibility=layer.default_visibility,
                created_at=layer.created_at
            ) for layer in layers
        ]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/ready", response_model=List[dict])
async def get_ready_layers():
    """Get all ready layers for map display with Martin tile URLs"""
    try:
        processor = get_spatial_processor()
        layers = processor.get_layer_list()
        return layers
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{layer_id}", response_model=SpatialLayerResponse)
async def get_spatial_layer(
    layer_id: UUID,
    db: Session = Depends(get_db)
):
    """Get spatial layer by ID"""
    layer = spatial_layer_crud.get_by_id(db, str(layer_id))
    if not layer:
        raise HTTPException(status_code=404, detail="Layer not found")

    return SpatialLayerResponse.from_orm(layer)


@router.put("/{layer_id}", response_model=SpatialLayerResponse)
async def update_spatial_layer(
    layer_id: UUID,
    layer_update: SpatialLayerUpdate,
    db: Session = Depends(get_db),
    # current_user = Depends(get_current_user)  # Uncomment when auth is ready
):
    """Update spatial layer metadata and styling"""
    layer = spatial_layer_crud.update(db, str(layer_id), layer_update)
    if not layer:
        raise HTTPException(status_code=404, detail="Layer not found")

    return SpatialLayerResponse.from_orm(layer)


@router.delete("/{layer_id}")
async def delete_spatial_layer(
    layer_id: UUID,
    db: Session = Depends(get_db),
    # current_user = Depends(get_current_user)  # Uncomment when auth is ready
):
    """Delete spatial layer and associated spatial table"""
    try:
        processor = get_spatial_processor()
        success, message = processor.delete_layer(str(layer_id))

        if success:
            return JSONResponse(
                status_code=200,
                content={"success": True, "message": message}
            )
        else:
            raise HTTPException(status_code=404, detail=message)

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{layer_id}/style")
async def update_layer_style(
    layer_id: UUID,
    style_data: dict,
    db: Session = Depends(get_db),
    # current_user = Depends(get_current_user)  # Uncomment when auth is ready
):
    """Update layer MapLibre style"""
    try:
        update_data = SpatialLayerUpdate(maplibre_style=style_data)
        layer = spatial_layer_crud.update(db, str(layer_id), update_data)

        if not layer:
            raise HTTPException(status_code=404, detail="Layer not found")

        return JSONResponse(
            status_code=200,
            content={
                "success": True,
                "message": "Style updated successfully",
                "style": layer.maplibre_style
            }
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{layer_id}/style")
async def get_layer_style(
    layer_id: UUID,
    db: Session = Depends(get_db)
):
    """Get layer MapLibre style"""
    layer = spatial_layer_crud.get_by_id(db, str(layer_id))
    if not layer:
        raise HTTPException(status_code=404, detail="Layer not found")

    return JSONResponse(
        status_code=200,
        content={
            "layer_id": str(layer.id),
            "layer_name": layer.layer_name,
            "display_name": layer.display_name,
            "geometry_type": layer.geometry_type,
            "style": layer.maplibre_style
        }
    )


@router.get("/{layer_id}/martin-config")
async def get_martin_config(
    layer_id: UUID,
    db: Session = Depends(get_db)
):
    """Get Martin tile service configuration for layer"""
    layer = spatial_layer_crud.get_by_id(db, str(layer_id))
    if not layer:
        raise HTTPException(status_code=404, detail="Layer not found")

    if layer.processing_status != LayerProcessingStatus.READY:
        raise HTTPException(
            status_code=400,
            detail=f"Layer is not ready. Status: {layer.processing_status}"
        )

    return JSONResponse(
        status_code=200,
        content={
            "layer_id": str(layer.id),
            "layer_name": layer.layer_name,
            "martin_layer_id": layer.martin_layer_id,
            "martin_url": layer.martin_url,
            "tile_url_template": layer.martin_url,
            "bounds": layer.bbox,
            "minzoom": layer.min_zoom,
            "maxzoom": layer.max_zoom,
            "geometry_type": layer.geometry_type,
            "feature_count": layer.feature_count
        }
    )


@router.get("/")
async def list_layers():
    """List all spatial layers"""
    return {"message": "Spatial layers endpoint"}
