"""
CRUD Operations for LastMile Processing
"""

from sqlalchemy.orm import Session
from sqlalchemy import desc, asc, and_, or_, func
from typing import List, Optional, Dict, Any
from datetime import datetime
import uuid

from .models import LastMileProcessingResult, SpatialLayer
from .schemas import (
    LastMileProcessingResultCreate,
    LastMileProcessingResultUpdate,
    ProcessingStatus,
    ProcessingResultQuery,
    SpatialLayerCreate,
    SpatialLayerUpdate,
    LayerProcessingStatus
)


class LastMileProcessingResultCRUD:
    """CRUD operations for LastMileProcessingResult"""

    @staticmethod
    def create(db: Session, obj_in: LastMileProcessingResultCreate) -> LastMileProcessingResult:
        """Create a new processing result record"""
        db_obj = LastMileProcessingResult(**obj_in.model_dump())
        db_obj.processing_started_at = datetime.utcnow()
        db.add(db_obj)
        db.commit()
        db.refresh(db_obj)
        return db_obj

    @staticmethod
    def get(db: Session, id: uuid.UUID) -> Optional[LastMileProcessingResult]:
        """Get processing result by ID"""
        return db.query(LastMileProcessingResult).filter(LastMileProcessingResult.id == id).first()

    @staticmethod
    def get_by_request_id(db: Session, request_id: str) -> Optional[LastMileProcessingResult]:
        """Get processing result by request_id"""
        return db.query(LastMileProcessingResult).filter(LastMileProcessingResult.request_id == request_id).first()

    @staticmethod
    def get_multi(
        db: Session,
        skip: int = 0,
        limit: int = 100,
        query_params: Optional[ProcessingResultQuery] = None
    ) -> List[LastMileProcessingResult]:
        """Get multiple processing results with filtering"""
        query = db.query(LastMileProcessingResult)

        if query_params:
            if query_params.status:
                query = query.filter(LastMileProcessingResult.processing_status == query_params.status)
            if query_params.created_by:
                query = query.filter(LastMileProcessingResult.created_by == query_params.created_by)
            if query_params.pulau:
                query = query.filter(LastMileProcessingResult.pulau == query_params.pulau)
            if query_params.date_from:
                query = query.filter(LastMileProcessingResult.created_at >= query_params.date_from)
            if query_params.date_to:
                query = query.filter(LastMileProcessingResult.created_at <= query_params.date_to)

        return query.order_by(desc(LastMileProcessingResult.created_at)).offset(skip).limit(limit).all()

    @staticmethod
    def update(db: Session, id: uuid.UUID, obj_in) -> Optional[LastMileProcessingResult]:
        """Update processing result"""
        db_obj = db.query(LastMileProcessingResult).filter(LastMileProcessingResult.id == id).first()
        if db_obj:
            # Handle both Pydantic models and dictionaries
            if hasattr(obj_in, 'model_dump'):
                update_data = obj_in.model_dump(exclude_unset=True)
            else:
                update_data = obj_in

            for field, value in update_data.items():
                if hasattr(db_obj, field):
                    setattr(db_obj, field, value)
            db.commit()
            db.refresh(db_obj)
        return db_obj

    @staticmethod
    def update_status(db: Session, id: uuid.UUID, status: ProcessingStatus, error_message: str = None) -> Optional[LastMileProcessingResult]:
        """Update processing status"""
        db_obj = db.query(LastMileProcessingResult).filter(LastMileProcessingResult.id == id).first()
        if db_obj:
            db_obj.processing_status = status
            if status == ProcessingStatus.COMPLETED:
                db_obj.processing_completed_at = datetime.utcnow()
                if db_obj.processing_started_at:
                    duration = (db_obj.processing_completed_at - db_obj.processing_started_at).total_seconds()
                    db_obj.processing_duration_seconds = int(duration)
            elif status == ProcessingStatus.FAILED:
                db_obj.processing_completed_at = datetime.utcnow()
                db_obj.error_message = error_message
            db.commit()
            db.refresh(db_obj)
        return db_obj

    @staticmethod
    def delete(db: Session, id: uuid.UUID) -> bool:
        """Delete processing result"""
        db_obj = db.query(LastMileProcessingResult).filter(LastMileProcessingResult.id == id).first()
        if db_obj:
            db.delete(db_obj)
            db.commit()
            return True
        return False

    @staticmethod
    def get_count(db: Session, query_params: Optional[ProcessingResultQuery] = None) -> int:
        """Get total count of processing results"""
        query = db.query(func.count(LastMileProcessingResult.id))

        if query_params:
            if query_params.status:
                query = query.filter(LastMileProcessingResult.processing_status == query_params.status)
            if query_params.created_by:
                query = query.filter(LastMileProcessingResult.created_by == query_params.created_by)
            if query_params.pulau:
                query = query.filter(LastMileProcessingResult.pulau == query_params.pulau)
            if query_params.date_from:
                query = query.filter(LastMileProcessingResult.created_at >= query_params.date_from)
            if query_params.date_to:
                query = query.filter(LastMileProcessingResult.created_at <= query_params.date_to)

        return query.scalar()

    @staticmethod
    def get_summary_stats(db: Session) -> Dict[str, Any]:
        """Get summary statistics"""
        total_jobs = db.query(func.count(LastMileProcessingResult.id)).scalar()
        pending_jobs = db.query(func.count(LastMileProcessingResult.id)).filter(
            LastMileProcessingResult.processing_status == ProcessingStatus.PENDING
        ).scalar()
        processing_jobs = db.query(func.count(LastMileProcessingResult.id)).filter(
            LastMileProcessingResult.processing_status == ProcessingStatus.PROCESSING
        ).scalar()
        completed_jobs = db.query(func.count(LastMileProcessingResult.id)).filter(
            LastMileProcessingResult.processing_status == ProcessingStatus.COMPLETED
        ).scalar()
        failed_jobs = db.query(func.count(LastMileProcessingResult.id)).filter(
            LastMileProcessingResult.processing_status == ProcessingStatus.FAILED
        ).scalar()

        total_requests = db.query(func.sum(LastMileProcessingResult.processed_requests)).scalar() or 0
        avg_duration = db.query(func.avg(LastMileProcessingResult.processing_duration_seconds)).filter(
            LastMileProcessingResult.processing_status == ProcessingStatus.COMPLETED
        ).scalar()

        return {
            "total_jobs": total_jobs,
            "pending_jobs": pending_jobs,
            "processing_jobs": processing_jobs,
            "completed_jobs": completed_jobs,
            "failed_jobs": failed_jobs,
            "total_requests_processed": total_requests,
            "average_processing_time_minutes": round(avg_duration / 60, 2) if avg_duration else None
        }


# Create instances for easy import
processing_result_crud = LastMileProcessingResultCRUD()

# Spatial Layer CRUD Operations
class SpatialLayerCRUD:
    """CRUD operations for SpatialLayer"""

    @staticmethod
    def create(db: Session, layer_data: SpatialLayerCreate) -> SpatialLayer:
        """Create a new spatial layer"""
        db_layer = SpatialLayer(**layer_data.model_dump())
        db.add(db_layer)
        db.commit()
        db.refresh(db_layer)
        return db_layer

    @staticmethod
    def get_by_id(db: Session, layer_id: str) -> Optional[SpatialLayer]:
        """Get spatial layer by ID"""
        return db.query(SpatialLayer).filter(SpatialLayer.id == layer_id).first()

    @staticmethod
    def get_by_layer_name(db: Session, layer_name: str) -> Optional[SpatialLayer]:
        """Get spatial layer by layer name"""
        return db.query(SpatialLayer).filter(SpatialLayer.layer_name == layer_name).first()

    @staticmethod
    def get_all(db: Session, skip: int = 0, limit: int = 100) -> List[SpatialLayer]:
        """Get all spatial layers with pagination"""
        return db.query(SpatialLayer).offset(skip).limit(limit).all()

    @staticmethod
    def get_ready_layers(db: Session) -> List[SpatialLayer]:
        """Get all ready spatial layers for map display"""
        return db.query(SpatialLayer).filter(
            SpatialLayer.processing_status == LayerProcessingStatus.READY
        ).all()

    @staticmethod
    def update(db: Session, layer_id: str, layer_update) -> Optional[SpatialLayer]:
        """Update spatial layer"""
        db_layer = db.query(SpatialLayer).filter(SpatialLayer.id == layer_id).first()
        if db_layer:
            # Handle both Pydantic models and dictionaries
            if hasattr(layer_update, 'model_dump'):
                update_data = layer_update.model_dump(exclude_unset=True)
            else:
                update_data = layer_update

            for field, value in update_data.items():
                if hasattr(db_layer, field):
                    setattr(db_layer, field, value)
            db.commit()
            db.refresh(db_layer)
        return db_layer

    @staticmethod
    def delete(db: Session, layer_id: str) -> bool:
        """Delete spatial layer"""
        db_layer = db.query(SpatialLayer).filter(SpatialLayer.id == layer_id).first()
        if db_layer:
            db.delete(db_layer)
            db.commit()
            return True
        return False

    @staticmethod
    def count(db: Session) -> int:
        """Get total count of spatial layers"""
        return db.query(SpatialLayer).count()

    @staticmethod
    def get_by_status(db: Session, status: LayerProcessingStatus) -> List[SpatialLayer]:
        """Get spatial layers by processing status"""
        return db.query(SpatialLayer).filter(SpatialLayer.processing_status == status).all()


# Create instance for easy access
spatial_layer_crud = SpatialLayerCRUD()