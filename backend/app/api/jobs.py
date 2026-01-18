from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from app.core.database import get_db
from app.models import AnalysisJob
from app.api.schemas import AnalysisJobResponse, AnalysisJobListResponse

router = APIRouter(prefix="/api/jobs", tags=["jobs"])


@router.get("", response_model=AnalysisJobListResponse)
async def list_jobs(
    skip: int = 0,
    limit: int = 20,
    repository_id: UUID | None = None,
    db: AsyncSession = Depends(get_db),
):
    """List analysis jobs."""
    query = select(AnalysisJob)
    if repository_id:
        query = query.where(AnalysisJob.repository_id == repository_id)
    query = query.offset(skip).limit(limit).order_by(AnalysisJob.created_at.desc())

    result = await db.execute(query)
    jobs = result.scalars().all()

    count_query = select(func.count()).select_from(AnalysisJob)
    if repository_id:
        count_query = count_query.where(AnalysisJob.repository_id == repository_id)
    count_result = await db.execute(count_query)
    total = count_result.scalar()

    return AnalysisJobListResponse(jobs=jobs, total=total)


@router.get("/{job_id}", response_model=AnalysisJobResponse)
async def get_job(
    job_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    """Get job details and progress."""
    result = await db.execute(select(AnalysisJob).where(AnalysisJob.id == job_id))
    job = result.scalar_one_or_none()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return job


@router.post("/{job_id}/cancel", response_model=AnalysisJobResponse)
async def cancel_job(
    job_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    """Cancel a running job."""
    from app.worker.celery_app import celery_app

    result = await db.execute(select(AnalysisJob).where(AnalysisJob.id == job_id))
    job = result.scalar_one_or_none()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    if job.status not in ["pending", "running"]:
        raise HTTPException(status_code=400, detail="Job cannot be cancelled")

    # Revoke Celery task
    celery_app.control.revoke(str(job_id), terminate=True)

    job.status = "failed"
    job.error_message = "Cancelled by user"
    await db.commit()
    await db.refresh(job)

    return job
