"""
CRUD Operations for LastMile Processing
"""

from sqlalchemy.orm import Session
from sqlalchemy import desc, asc, and_, or_, func
from typing import List, Optional, Dict, Any
from datetime import datetime
import uuid

from .models import LastMileProcessingResult
from .schemas import (
    LastMileProcessingResultCreate,
    LastMileProcessingResultUpdate,
    ProcessingStatus,
    ProcessingResultQuery
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