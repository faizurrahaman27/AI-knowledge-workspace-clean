"""
Background Worker Infrastructure

Async job processing for autonomous knowledge processing.
"""

import uuid
import asyncio
from typing import List, Dict, Any, Optional, Callable
from datetime import datetime, timedelta
from enum import Enum
import logging

from sqlalchemy.orm import Session

from src.autonomous.models import BackgroundJob, JobStatus
from src.core.logging import logger

# Try to import celery, but make it optional
try:
    from celery import Celery
    CELERY_AVAILABLE = True
except ImportError:
    CELERY_AVAILABLE = False


class JobType(str, Enum):
    """Background job types."""
    EXTRACT_KNOWLEDGE = "extract_knowledge"
    GENERATE_EMBEDDINGS = "generate_embeddings"
    BUILD_KNOWLEDGE_GRAPH = "build_knowledge_graph"
    GENERATE_QUESTIONS = "generate_questions"
    GENERATE_FLASHCARDS = "generate_flashcards"
    CREATE_NOTEBOOK = "create_notebook"
    UPDATE_TIMELINE = "update_timeline"
    GENERATE_SUMMARY = "generate_summary"
    VALIDATE_KNOWLEDGE = "validate_knowledge"
    ANALYZE_DOCUMENT = "analyze_document"


class BackgroundWorker:
    """
    Background worker for async processing.
    
    Features:
    - Job queuing
    - Progress tracking
    - Retry logic
    - Priority scheduling
    - Status updates
    """
    
    def __init__(self, db: Session):
        """Initialize the background worker."""
        self.db = db
        self._running_jobs: Dict[str, asyncio.Task] = {}
    
    def create_job(
        self,
        user_id: int,
        job_type: str,
        job_name: str,
        target_type: Optional[str] = None,
        target_id: Optional[str] = None,
        input_data: Optional[Dict] = None,
        priority: int = 5,
        scheduled_at: Optional[datetime] = None
    ) -> BackgroundJob:
        """
        Create a background job.
        
        Args:
            user_id: User ID
            job_type: Type of job
            job_name: Job name
            target_type: Target entity type
            target_id: Target entity ID
            input_data: Job input data
            priority: Job priority (1-10, lower = higher priority)
            scheduled_at: When to run (None = run immediately)
            
        Returns:
            Created job
        """
        job_id = f"job_{uuid.uuid4().hex[:12]}"
        
        job = BackgroundJob(
            job_id=job_id,
            job_type=job_type,
            job_name=job_name,
            user_id=user_id,
            target_type=target_type,
            target_id=target_id,
            input_data=input_data,
            status=JobStatus.PENDING.value,
            priority=priority,
            scheduled_at=scheduled_at
        )
        
        self.db.add(job)
        self.db.commit()
        self.db.refresh(job)
        
        logger.info(f"Created background job: {job_id} ({job_type})")
        
        return job
    
    def get_job(self, job_id: str) -> Optional[BackgroundJob]:
        """Get job by ID."""
        return self.db.query(BackgroundJob).filter(
            BackgroundJob.job_id == job_id
        ).first()
    
    def get_pending_jobs(
        self,
        limit: int = 100,
        user_id: Optional[int] = None
    ) -> List[BackgroundJob]:
        """Get pending jobs sorted by priority."""
        query = self.db.query(BackgroundJob).filter(
            BackgroundJob.status == JobStatus.PENDING.value
        )
        
        if user_id:
            query = query.filter(BackgroundJob.user_id == user_id)
        
        return query.order_by(
            BackgroundJob.priority,
            BackgroundJob.created_at
        ).limit(limit).all()
    
    def start_job(self, job_id: str) -> BackgroundJob:
        """Mark job as started."""
        job = self.get_job(job_id)
        
        if not job:
            raise ValueError(f"Job {job_id} not found")
        
        job.status = JobStatus.RUNNING.value
        job.started_at = datetime.utcnow()
        self.db.commit()
        self.db.refresh(job)
        
        logger.info(f"Started job: {job_id}")
        
        return job
    
    def update_progress(
        self,
        job_id: str,
        progress: float,
        current_step: Optional[str] = None
    ) -> BackgroundJob:
        """Update job progress."""
        job = self.get_job(job_id)
        
        if not job:
            raise ValueError(f"Job {job_id} not found")
        
        job.progress = min(progress, 1.0)
        if current_step:
            job.current_step = current_step
        
        self.db.commit()
        self.db.refresh(job)
        
        return job
    
    def complete_job(
        self,
        job_id: str,
        output_data: Optional[Dict] = None
    ) -> BackgroundJob:
        """Mark job as completed."""
        job = self.get_job(job_id)
        
        if not job:
            raise ValueError(f"Job {job_id} not found")
        
        job.status = JobStatus.COMPLETED.value
        job.progress = 1.0
        job.completed_at = datetime.utcnow()
        
        if output_data:
            job.output_data = output_data
        
        if job.started_at:
            job.actual_duration_seconds = int(
                (job.completed_at - job.started_at).total_seconds()
            )
        
        self.db.commit()
        self.db.refresh(job)
        
        logger.info(f"Completed job: {job_id}")
        
        return job
    
    def fail_job(
        self,
        job_id: str,
        error_message: str
    ) -> BackgroundJob:
        """Mark job as failed."""
        job = self.get_job(job_id)
        
        if not job:
            raise ValueError(f"Job {job_id} not found")
        
        job.status = JobStatus.FAILED.value
        job.error_message = error_message
        job.completed_at = datetime.utcnow()
        
        self.db.commit()
        self.db.refresh(job)
        
        logger.error(f"Job {job_id} failed: {error_message}")
        
        return job
    
    def retry_job(self, job_id: str) -> BackgroundJob:
        """Retry a failed job."""
        job = self.get_job(job_id)
        
        if not job:
            raise ValueError(f"Job {job_id} not found")
        
        if job.retry_count >= job.max_retries:
            raise ValueError(f"Job {job_id} has exceeded max retries")
        
        job.status = JobStatus.PENDING.value
        job.retry_count += 1
        job.error_message = None
        job.completed_at = None
        job.progress = 0.0
        
        self.db.commit()
        self.db.refresh(job)
        
        logger.info(f"Retrying job: {job_id} (attempt {job.retry_count})")
        
        return job
    
    def cancel_job(self, job_id: str) -> BackgroundJob:
        """Cancel a job."""
        job = self.get_job(job_id)
        
        if not job:
            raise ValueError(f"Job {job_id} not found")
        
        if job.status == JobStatus.RUNNING.value:
            raise ValueError(f"Cannot cancel running job {job_id}")
        
        job.status = JobStatus.CANCELLED.value
        job.completed_at = datetime.utcnow()
        
        self.db.commit()
        self.db.refresh(job)
        
        logger.info(f"Cancelled job: {job_id}")
        
        return job
    
    def get_user_jobs(
        self,
        user_id: int,
        status: Optional[str] = None,
        limit: int = 50
    ) -> List[BackgroundJob]:
        """Get user's jobs."""
        query = self.db.query(BackgroundJob).filter(
            BackgroundJob.user_id == user_id
        )
        
        if status:
            query = query.filter(BackgroundJob.status == status)
        
        return query.order_by(
            BackgroundJob.created_at.desc()
        ).limit(limit).all()
    
    def cleanup_old_jobs(self, days: int = 30) -> int:
        """Clean up old completed/failed jobs."""
        cutoff = datetime.utcnow() - timedelta(days=days)
        
        count = self.db.query(BackgroundJob).filter(
            BackgroundJob.status.in_([
                JobStatus.COMPLETED.value,
                JobStatus.FAILED.value,
                JobStatus.CANCELLED.value
            ]),
            BackgroundJob.completed_at < cutoff
        ).delete()
        
        self.db.commit()
        
        logger.info(f"Cleaned up {count} old jobs")
        
        return count


class JobExecutor:
    """
    Job executor that processes background jobs.
    
    Provides async execution of knowledge processing tasks.
    """
    
    def __init__(self, db: Session):
        """Initialize the job executor."""
        self.db = db
        self.worker = BackgroundWorker(db)
        self._handlers: Dict[str, Callable] = {}
    
    def register_handler(self, job_type: str, handler: Callable):
        """Register a job handler."""
        self._handlers[job_type] = handler
    
    async def execute_job(self, job_id: str) -> Dict[str, Any]:
        """
        Execute a job.
        
        Args:
            job_id: Job ID
            
        Returns:
            Execution result
        """
        job = self.worker.get_job(job_id)
        
        if not job:
            return {"success": False, "error": f"Job {job_id} not found"}
        
        # Start job
        self.worker.start_job(job_id)
        
        try:
            # Get handler
            handler = self._handlers.get(job.job_type)
            
            if not handler:
                # Default handler
                result = await self._default_handler(job)
            else:
                # Execute handler
                result = await handler(job)
            
            # Complete job
            self.worker.complete_job(job_id, result)
            
            return {"success": True, "result": result}
            
        except Exception as e:
            logger.exception(f"Job {job_id} failed")
            self.worker.fail_job(job_id, str(e))
            return {"success": False, "error": str(e)}
    
    async def _default_handler(self, job: BackgroundJob) -> Dict[str, Any]:
        """Default job handler."""
        # Simulate processing
        await asyncio.sleep(1)
        
        return {
            "job_type": job.job_type,
            "job_name": job.job_name,
            "processed_at": datetime.utcnow().isoformat()
        }
    
    async def process_queue(self, max_jobs: int = 10):
        """Process pending jobs from queue."""
        jobs = self.worker.get_pending_jobs(limit=max_jobs)
        
        for job in jobs:
            await self.execute_job(job.job_id)


# Factory functions
def get_background_worker(db: Session) -> BackgroundWorker:
    """Get background worker instance."""
    return BackgroundWorker(db)


def get_job_executor(db: Session) -> JobExecutor:
    """Get job executor instance."""
    return JobExecutor(db)
