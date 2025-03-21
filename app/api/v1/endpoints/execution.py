from typing import Any, List, Dict, Optional
import uuid
import logging
from pydantic import BaseModel
from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks, Request

from app.core.security import get_current_user
from app.services.execution import ExecutionService
from app.models.batch import BatchExecutionCreate, BatchStatus
from app.models.test import TestCase, ValidationConfig
from app.models.results import JobInfo
from app.core.queue_instance import task_queue

router = APIRouter()
execution_service = ExecutionService()
logger = logging.getLogger(__name__)

class ValidationRequest(BaseModel):
    validation_id: str
    validation_type: str
    validation_parameters: Dict[str, Any]

class TurnRequest(BaseModel):
    turn_id: str
    order: int
    user_input: str
    validations: List[ValidationRequest]

class TestRequest(BaseModel):
    test_id: str
    turns: List[TurnRequest]
    credentials: Dict[str, str]
    config: Optional[Dict[str, Any]] = None

class BatchExecutionRequest(BaseModel):
    batch_id: str
    tests: List[TestRequest]


@router.post("/execute", response_model=JobInfo)
async def execute_batch(
    request: BatchExecutionRequest,
    req: Request,
    current_user: dict = Depends(get_current_user)
) -> Any:
    """
    Execute a batch of tests against an AI agent.
    
    This endpoint accepts a batch of tests to execute and returns a job ID
    that can be used to check the status of the execution.
    """
    # Generate a unique job ID
    job_id = str(uuid.uuid4())
    
    # Log the request with job_id
    logger.info(
        f"Received batch execution request: batch_id={request.batch_id}, tests={len(request.tests)}",
        extra={
            "request_id": getattr(req.state, "request_id", None),
            "job_id": job_id,
            "batch_id": request.batch_id,
            "test_count": len(request.tests),
            "user": current_user.get("username")
        }
    )
    
    # Add the job to the task queue
    await task_queue.enqueue_job(
        job_id,
        execution_service.execute_batch,
        batch_id=request.batch_id,
        tests=request.tests
    )
    
    return {
        "job_id": job_id,
        "status": "queued",
        "message": f"Batch execution queued with {len(request.tests)} tests"
    }


@router.get("/status/{job_id}", response_model=BatchStatus)
async def get_batch_status(
    job_id: str,
    req: Request,
    current_user: dict = Depends(get_current_user)
) -> Any:
    """
    Get the status of a batch execution job.
    """
    logger.info(
        f"Getting status for job: {job_id}",
        extra={
            "request_id": getattr(req.state, "request_id", None),
            "job_id": job_id,
            "user": current_user.get("username")
        }
    )
    
    status = execution_service.get_batch_status(job_id)
    if not status:
        logger.warning(
            f"Job ID {job_id} not found",
            extra={
                "request_id": getattr(req.state, "request_id", None),
                "job_id": job_id
            }
        )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Job ID {job_id} not found"
        )
    
    return status


@router.get("/queue/status")
async def get_queue_status(
    current_user: dict = Depends(get_current_user)
) -> Any:
    """
    Get the status of the task queue.
    """
    return task_queue.get_status()