from typing import Any, Dict
from fastapi import APIRouter, Depends, HTTPException, status

from app.core.security import get_current_user
from app.services.execution import ExecutionService
from app.models.results import BatchResults

router = APIRouter()
execution_service = ExecutionService()


@router.get("/results/{job_id}", response_model=BatchResults)
async def get_batch_results(
    job_id: str,
    include_scraped_content: bool = False,
    current_user: dict = Depends(get_current_user)
) -> Any:
    """
    Get the complete results for a batch execution.
    
    Parameters:
    - job_id: The ID of the batch execution job
    - include_scraped_content: Whether to include scraped content in the results (can be large)
    """
    results = execution_service.get_batch_results(job_id, include_scraped_content)
    if not results:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Results for job ID {job_id} not found"
        )
    
    return results
