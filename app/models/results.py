from typing import List, Dict, Any, Optional
from pydantic import BaseModel
from app.models.validation import ValidationResult


class JobInfo(BaseModel):
    """Model for job information."""
    job_id: str
    status: str
    message: Optional[str] = None


class TurnResult(BaseModel):
    """Model for turn result."""
    turn_id: str
    order: int
    user_input: str
    agent_response: str
    scraped_content: Optional[str] = None
    response_time_ms: int
    validations_total: int
    validations_passed: int
    validations_failed: int
    validation_results: List[ValidationResult]


class TestResult(BaseModel):
    """Model for test result."""
    test_id: str
    status: str
    started_at: str
    completed_at: Optional[str] = None
    error: Optional[str] = None
    total_validations: int
    passed_validations: int
    failed_validations: int
    pass_rate: float
    avg_response_time: float
    turn_results: List[TurnResult]


class BatchResults(BaseModel):
    """Model for batch results."""
    job_id: str
    batch_id: str
    status: str
    started_at: str
    completed_at: Optional[str] = None
    total_tests: int
    completed_tests: int
    failed_tests: int
    total_validations: int
    passed_validations: int
    failed_validations: int
    pass_rate: float
    avg_response_time: float
    test_results: List[TestResult]
    error: Optional[str] = None
