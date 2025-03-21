from typing import Any, List, Dict, Optional
import uuid
from pydantic import BaseModel
from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks

from app.core.security import get_current_user
from app.services.execution import ExecutionService
from app.models.batch import BatchExecutionCreate, BatchStatus
from app.models.test import TestCase, ValidationConfig
from app.models.results import JobInfo

router = APIRouter()
execution_service = ExecutionService()

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
    background_tasks: BackgroundTasks,
    current_user: dict = Depends(get_current_user)
) -> Any:
    """
    Execute a batch of tests against an AI agent.
    
    This endpoint accepts a batch of tests to execute and returns a job ID
    that can be used to check the status of the execution.
    """
    # Generate a unique job ID
    job_id = str(uuid.uuid4())
    
    # Start the execution in a background task
    background_tasks.add_task(
        execution_service.execute_batch,
        job_id=job_id,
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
    current_user: dict = Depends(get_current_user)
) -> Any:
    """
    Get the status of a batch execution job.
    """
    status = execution_service.get_batch_status(job_id)
    if not status:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Job ID {job_id} not found"
        )
    
    return status
