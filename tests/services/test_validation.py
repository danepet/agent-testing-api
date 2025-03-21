import pytest
import asyncio
from app.services.validation import ValidationService


@pytest.fixture
def validation_service():
    """Fixture for validation service."""
    return ValidationService()


@pytest.mark.asyncio
async def test_validate_contains(validation_service):
    """Test contains validation."""
    # Test with matching text
    result = validation_service._validate_contains(
        "Hello, world!", {"text": "world", "case_sensitive": True}
    )
    assert result["passed"] is True
    assert result["score"] == 1.0
    
    # Test with non-matching text
    result = validation_service._validate_contains(
        "Hello, world!", {"text": "universe", "case_sensitive": True}
    )
    assert result["passed"] is False
    assert result["score"] == 0.0
    
    # Test case sensitivity
    result = validation_service._validate_contains(
        "Hello, World!", {"text": "world", "case_sensitive": True}
    )
    assert result["passed"] is False
    
    result = validation_service._validate_contains(
        "Hello, World!", {"text": "world", "case_sensitive": False}
    )
    assert result["passed"] is True


@pytest.mark.asyncio
async def test_validate_not_contains(validation_service):
    """Test not_contains validation."""
    # Test with excluded text
    result = validation_service._validate_not_contains(
        "Hello, world!", {"text": "universe", "case_sensitive": True}
    )
    assert result["passed"] is True
    assert result["score"] == 1.0
    
    # Test with included text
    result = validation_service._validate_not_contains(
        "Hello, world!", {"text": "world", "case_sensitive": True}
    )
    assert result["passed"] is False
    assert result["score"] == 0.0
    
    # Test case sensitivity
    result = validation_service._validate_not_contains(
        "Hello, World!", {"text": "world", "case_sensitive": True}
    )
    assert result["passed"] is True
    
    result = validation_service._validate_not_contains(
        "Hello, World!", {"text": "world", "case_sensitive": False}
    )
    assert result["passed"] is False


@pytest.mark.asyncio
async def test_validate_regex(validation_service):
    """Test regex validation."""
    # Test with matching pattern
    result = validation_service._validate_regex(
        "Hello, world!", {"pattern": r"world", "expected_match": True}
    )
    assert result["passed"] is True
    assert result["score"] == 1.0
    assert result["matches"] == ["world"]
    
    # Test with non-matching pattern
    result = validation_service._validate_regex(
        "Hello, world!", {"pattern": r"universe", "expected_match": True}
    )
    assert result["passed"] is False
    assert result["score"] == 0.0
    assert result["matches"] == []
    
    # Test expected_match=False
    result = validation_service._validate_regex(
        "Hello, world!", {"pattern": r"universe", "expected_match": False}
    )
    assert result["passed"] is True
    assert result["score"] == 1.0
    
    # Test invalid regex
    result = validation_service._validate_regex(
        "Hello, world!", {"pattern": r"[", "expected_match": True}
    )
    assert result["passed"] is False
    assert result["score"] == 0.0
    assert "Invalid regex pattern" in result["details"]


@pytest.mark.asyncio
async def test_validate_method(validation_service):
    """Test validate method calls the correct validation function."""
    # Test contains validation
    result = await validation_service.validate(
        "contains", "Hello, world!", {"text": "world", "case_sensitive": True}
    )
    assert result["type"] == "contains"
    assert result["passed"] is True
    
    # Test not_contains validation
    result = await validation_service.validate(
        "not_contains", "Hello, world!", {"text": "universe", "case_sensitive": True}
    )
    assert result["type"] == "not_contains"
    assert result["passed"] is True
    
    # Test regex validation
    result = await validation_service.validate(
        "regex", "Hello, world!", {"pattern": r"world", "expected_match": True}
    )
    assert result["type"] == "regex"
    assert result["passed"] is True
    
    # Test unknown validation type
    result = await validation_service.validate(
        "unknown", "Hello, world!", {}
    )
    assert result["passed"] is False
    assert "Unknown validation type" in result["details"]


@pytest.mark.asyncio
async def test_advanced_validations(validation_service):
    """Test advanced validations."""
    # These tests are for simulated advanced validations
    # In a real implementation, you would use actual validation models
    result = await validation_service._simulate_advanced_validation(
        "Hello, world!", "answer_relevancy", {"threshold": 0.5}
    )
    assert result["type"] == "answer_relevancy"
    assert "score" in result
    assert "passed" in result
    
    result = await validation_service._simulate_advanced_validation(
        "Hello, world!", "contextual_relevancy", {"threshold": 0.5}
    )
    assert result["type"] == "contextual_relevancy"
    
    result = await validation_service._simulate_advanced_validation(
        "Hello, world!", "faithfulness", {"threshold": 0.5}
    )
    assert result["type"] == "faithfulness"