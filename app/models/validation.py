from typing import List, Dict, Any, Optional
from pydantic import BaseModel


class ValidationResult(BaseModel):
    """Model for validation result."""
    validation_id: str
    validation_type: str
    is_passed: bool
    score: Optional[float] = None
    details: Optional[Dict[str, Any]] = None
