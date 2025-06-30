"""
Spatial Layer Processor for handling file uploads and Martin tile service integration
"""

import os
import re
import uuid
import pandas as pd
import geopandas as gpd
from pathlib import Path
from typing import Optional, Dict, Any, List, Tuple
from sqlalchemy import create_engine, text, inspect
from sqlalchemy.orm import Session
from geoalchemy2 import Geometry
from geoalchemy2.functions import ST_AsText, ST_Envelope, ST_Transform

from ..database.config import SessionLocal
from ..database.models import SpatialLayer
from ..database.crud import spatial_layer_crud
from ..database.schemas import SpatialLayerCreate, LayerProcessingStatus, LayerFileType


class SpatialLayerProcessor:
    """Service for processing spatial layer uploads"""

    def __init__(self, db_url: str, martin_base_url: str = "http://localhost:5000"):
        self.db_url = db_url
        self.martin_base_url = martin_base_url
        self.engine = create_engine(db_url)

    def _sanitize_layer_name(self, filename: str) -> str:
        """Sanitize filename to create valid PostgreSQL table name"""
        # Remove file extension
        name = Path(filename).stem

        # Convert to lowercase and replace invalid characters
        name = re.sub(r'[^a-zA-Z0-9_]', '_', name.lower())

        # Ensure it starts with a letter or underscore
        if name[0].isdigit():
            name = f"layer_{name}"

        # Add unique suffix to avoid conflicts
        unique_suffix = str(uuid.uuid4())[:8]
        return f"{name}_{unique_suffix}"

    def _detect_file_type(self, file_path: str) -> LayerFileType:
        """Detect file type from file extension"""
        extension = Path(file_path).suffix.lower()

        if extension == '.parquet':
            # Check if it's geoparquet by looking for geometry column
            try:
                df = pd.read_parquet(file_path)
                if any('geom' in col.lower() for col in df.columns):
                    return LayerFileType.GEOPARQUET
                return LayerFileType.PARQUET
            except:
                return LayerFileType.PARQUET
        elif extension == '.geojson':
            return LayerFileType.GEOJSON
        elif extension == '.shp':
            return LayerFileType.SHAPEFILE
        else:
            raise ValueError(f"Unsupported file type: {extension}")

    def _load_spatial_file(self, file_path: str, target_srid: int = 4326) -> gpd.GeoDataFrame:
        """Load spatial file into GeoDataFrame"""
        file_type = self._detect_file_type(file_path)

        if file_type in [LayerFileType.PARQUET, LayerFileType.GEOPARQUET]:
            # For parquet files, we need to handle geometry column
            df = pd.read_parquet(file_path)

            # Look for geometry column (common names)
            geom_cols = [col for col in df.columns if 'geom' in col.lower() or 'shape' in col.lower()]

            if geom_cols:
                # Convert to GeoDataFrame
                gdf = gpd.GeoDataFrame(df, geometry=geom_cols[0])
            else:
                # Check if there are lat/lon columns for point data
                lat_cols = [col for col in df.columns if any(name in col.lower() for name in ['lat', 'y', 'latitude'])]
                lon_cols = [col for col in df.columns if any(name in col.lower() for name in ['lon', 'lng', 'x', 'longitude'])]

                if lat_cols and lon_cols:
                    # Create geometry from lat/lon
                    gdf = gpd.GeoDataFrame(
                        df,
                        geometry=gpd.points_from_xy(df[lon_cols[0]], df[lat_cols[0]]),
                        crs=f"EPSG:{target_srid}"
                    )
                else:
                    raise ValueError("No geometry column or lat/lon columns found in parquet file")

        elif file_type == LayerFileType.GEOJSON:
            gdf = gpd.read_file(file_path)

        elif file_type == LayerFileType.SHAPEFILE:
            gdf = gpd.read_file(file_path)

        else:
            raise ValueError(f"Unsupported file type: {file_type}")

        # Ensure CRS is set and convert to target SRID if needed
        if gdf.crs is None:
            gdf.set_crs(f"EPSG:{target_srid}", inplace=True)
        elif gdf.crs.to_epsg() != target_srid:
            gdf = gdf.to_crs(f"EPSG:{target_srid}")

        return gdf

    def _get_geometry_type(self, gdf: gpd.GeoDataFrame) -> str:
        """Get the predominant geometry type"""
        geom_types = gdf.geometry.geom_type.value_counts()
        return geom_types.index[0]  # Most common geometry type

    def _calculate_bbox(self, gdf: gpd.GeoDataFrame) -> List[float]:
        """Calculate bounding box"""
        bounds = gdf.total_bounds
        return [bounds[0], bounds[1], bounds[2], bounds[3]]  # [minx, miny, maxx, maxy]

    def _create_spatial_table(self, gdf: gpd.GeoDataFrame, table_name: str, srid: int = 4326) -> None:
        """Create spatial table in PostGIS database"""
        # Save GeoDataFrame to PostGIS
        gdf.to_postgis(
            table_name,
            self.engine,
            if_exists='replace',
            index=False,
            chunksize=1000
        )

        # Create spatial index
        with self.engine.connect() as conn:
            conn.execute(text(f"CREATE INDEX IF NOT EXISTS {table_name}_geom_idx ON {table_name} USING GIST (geometry);"))
            conn.commit()

    def _generate_default_style(self, geometry_type: str) -> Dict[str, Any]:
        """Generate default MapLibre style based on geometry type"""
        if geometry_type.lower() == 'point':
            return {
                "type": "circle",
                "paint": {
                    "circle-radius": 5,
                    "circle-color": "#3498db",
                    "circle-stroke-width": 1,
                    "circle-stroke-color": "#ffffff"
                }
            }
        elif geometry_type.lower() in ['linestring', 'multilinestring']:
            return {
                "type": "line",
                "paint": {
                    "line-color": "#e74c3c",
                    "line-width": 2
                }
            }
        elif geometry_type.lower() in ['polygon', 'multipolygon']:
            return {
                "type": "fill",
                "paint": {
                    "fill-color": "#2ecc71",
                    "fill-opacity": 0.6,
                    "fill-outline-color": "#27ae60"
                }
            }
        else:
            # Default style
            return {
                "type": "circle",
                "paint": {
                    "circle-radius": 3,
                    "circle-color": "#95a5a6"
                }
            }

    def _update_martin_config(self, layer_name: str) -> str:
        """Update Martin configuration to include new layer and return tile URL"""
        # Martin will auto-discover spatial tables in PostGIS
        # Return the tile URL format for this layer
        return f"{self.martin_base_url}/{layer_name}/{{z}}/{{x}}/{{y}}.pbf"

    async def process_upload(
        self,
        file_path: str,
        display_name: str,
        description: Optional[str] = None,
        target_srid: int = 4326,
        created_by: Optional[str] = None,
        custom_style: Optional[Dict[str, Any]] = None
    ) -> Tuple[bool, str, Optional[str]]:
        """
        Process uploaded spatial file

        Returns:
            (success: bool, message: str, layer_id: Optional[str])
        """
        try:
            # Generate unique layer name
            layer_name = self._sanitize_layer_name(Path(file_path).name)

            # Create initial database record
            db = SessionLocal()
            try:
                layer_create = SpatialLayerCreate(
                    layer_name=layer_name,
                    display_name=display_name,
                    description=description,
                    original_filename=Path(file_path).name,
                    file_type=self._detect_file_type(file_path),
                    file_size_bytes=os.path.getsize(file_path),
                    srid=target_srid,
                    created_by=created_by,
                    maplibre_style=custom_style or {}
                )

                db_layer = spatial_layer_crud.create(db, layer_create)
                layer_id = str(db_layer.id)
            finally:
                db.close()

            # Update status to processing
            db = SessionLocal()
            try:
                spatial_layer_crud.update(
                    db,
                    layer_id,
                    {"processing_status": LayerProcessingStatus.PROCESSING}
                )
            finally:
                db.close()

            # Load and process spatial file
            gdf = self._load_spatial_file(file_path, target_srid)

            # Get spatial metadata
            geometry_type = self._get_geometry_type(gdf)
            bbox = self._calculate_bbox(gdf)
            feature_count = len(gdf)

            # Create spatial table in PostGIS
            self._create_spatial_table(gdf, layer_name, target_srid)

            # Generate Martin tile URL
            martin_url = self._update_martin_config(layer_name)

            # Generate default style if not provided
            if not custom_style:
                custom_style = self._generate_default_style(geometry_type)

            # Update database record with results
            db = SessionLocal()
            try:
                update_data = {
                    "processing_status": LayerProcessingStatus.READY,
                    "geometry_type": geometry_type,
                    "bbox": bbox,
                    "feature_count": feature_count,
                    "martin_layer_id": layer_name,
                    "martin_url": martin_url,
                    "maplibre_style": custom_style,
                    "metadata_info": {
                        "columns": list(gdf.columns),
                        "crs": str(gdf.crs),
                        "bounds": bbox
                    }
                }

                spatial_layer_crud.update(db, layer_id, update_data)
            finally:
                db.close()

            return True, f"Layer '{display_name}' processed successfully", layer_id

        except Exception as e:
            # Update database record with error
            if 'layer_id' in locals():
                db = SessionLocal()
                try:
                    spatial_layer_crud.update(
                        db,
                        layer_id,
                        {
                            "processing_status": LayerProcessingStatus.ERROR,
                            "error_message": str(e)
                        }
                    )
                finally:
                    db.close()

            return False, f"Error processing layer: {str(e)}", None

    def get_layer_list(self) -> List[Dict[str, Any]]:
        """Get list of all ready layers for map display"""
        db = SessionLocal()
        try:
            layers = spatial_layer_crud.get_ready_layers(db)

            return [
                {
                    "id": str(layer.id),
                    "layer_name": layer.layer_name,
                    "display_name": layer.display_name,
                    "description": layer.description,
                    "geometry_type": layer.geometry_type,
                    "feature_count": layer.feature_count,
                    "martin_url": layer.martin_url,
                    "maplibre_style": layer.maplibre_style,
                    "default_visibility": layer.default_visibility,
                    "min_zoom": layer.min_zoom,
                    "max_zoom": layer.max_zoom,
                    "bbox": layer.bbox,
                    "created_at": layer.created_at.isoformat() if layer.created_at else None
                }
                for layer in layers
            ]

        finally:
            db.close()

    def delete_layer(self, layer_id: str) -> Tuple[bool, str]:
        """Delete layer from database and drop spatial table"""
        try:
            db = SessionLocal()
            try:
                layer = spatial_layer_crud.get_by_id(db, layer_id)
                if not layer:
                    return False, "Layer not found"

                table_name = layer.layer_name

                # Drop spatial table
                with self.engine.connect() as conn:
                    conn.execute(text(f"DROP TABLE IF EXISTS {table_name};"))
                    conn.commit()

                # Delete from database
                spatial_layer_crud.delete(db, layer_id)

                return True, "Layer deleted successfully"

            finally:
                db.close()

        except Exception as e:
            return False, f"Error deleting layer: {str(e)}"


# Create default instance
def get_spatial_processor() -> SpatialLayerProcessor:
    """Get spatial layer processor instance"""
    from ..database.config import DATABASE_URL
    from ..config import settings
    return SpatialLayerProcessor(
        db_url=DATABASE_URL,
        martin_base_url=getattr(settings, 'martin_base_url', 'http://localhost:5000')
    )