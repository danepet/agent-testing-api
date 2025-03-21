from typing import List, Dict, Any, Optional
from pydantic import BaseModel


class ValidationConfig(BaseModel):
    """Model for validation configuration."""
    validation_id: str
    validation_type: str
    validation_parameters: Dict[str, Any]


class ConversationTurn(BaseModel):
    """Model for a conversation turn."""
    turn_id: str
    order: int
    user_input: str
    validations: List[ValidationConfig]


class TestCase(BaseModel):
    """Model for a test case."""
    test_id: str
    name: str
    description: Optional[str] = None
    turns: List[ConversationTurn]
