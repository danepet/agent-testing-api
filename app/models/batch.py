from typing import List, Dict, Any, Optional
from pydantic import BaseModel
from datetime import datetime


class BatchExecutionCreate(BaseModel):
    """Model for creating a batch execution."""
    batch_id: str
    tests: List[str]
    credentials: Optional[Dict[str, str]] = None
    config: Optional[Dict[str, Any]] = None


class BatchStatus(BaseModel):
    """Model for batch execution status."""
    job_id: str
    batch_id: str
    status: str
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    progress: int = 0
    total_tests: int = 0
    completed_tests: int = 0
    failed_tests: int = 0
    current_test_id: Optional[str] = None
    current_turn: Optional[int] = None
    error: Optional[str] = None
