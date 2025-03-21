import pytest
import uuid
from datetime import datetime
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.exc import SQLAlchemyError

from app.db.models import Base, Job, TestResult, TurnResult, ValidationResult
from app.db.repositories.job_repository import JobRepository


@pytest.fixture
def db_session():
    """Create a test database session."""
    # Create an in-memory SQLite database for testing
    engine = create_engine("sqlite:///:memory:")
    
    # Create all tables
    Base.metadata.create_all(engine)
    
    # Create session
    TestingSessionLocal = sessionmaker(bind=engine)
    db = TestingSessionLocal()
    
    try:
        yield db
    finally:
        db.close()
        Base.metadata.drop_all(engine)


@pytest.fixture
def job_repository():
    """Create a job repository for testing."""
    return JobRepository()


def test_create_job(db_session, job_repository):
    """Test creating a job."""
    job_id = str(uuid.uuid4())
    batch_id = "test-batch"
    total_tests = 5
    
    job = job_repository.create_job(db_session, job_id, batch_id, total_tests)
    
    assert job.id == job_id
    assert job.batch_id == batch_id
    assert job.total_tests == total_tests
    assert job.status == "queued"
    assert job.started_at is not None
    
    # Check that the job is in the database
    db_job = db_session.query(Job).filter(Job.id == job_id).first()
    assert db_job is not None
    assert db_job.id == job_id


def test_get_job(db_session, job_repository):
    """Test getting a job."""
    # Create a job
    job_id = str(uuid.uuid4())
    job = Job(
        id=job_id,
        batch_id="test-batch",
        status="running",
        started_at=datetime.utcnow(),
        total_tests=5
    )
    db_session.add(job)
    db_session.commit()
    
    # Get the job
    retrieved_job = job_repository.get_job(db_session, job_id)
    
    assert retrieved_job is not None
    assert retrieved_job.id == job_id
    assert retrieved_job.batch_id == "test-batch"
    
    # Test getting a non-existent job
    non_existent_job = job_repository.get_job(db_session, "non-existent-id")
    assert non_existent_job is None


def test_update_job_status(db_session, job_repository):
    """Test updating job status."""
    # Create a job
    job_id = str(uuid.uuid4())
    job = Job(
        id=job_id,
        batch_id="test-batch",
        status="running",
        started_at=datetime.utcnow(),
        total_tests=5
    )
    db_session.add(job)
    db_session.commit()
    
    # Update job status
    updated_job = job_repository.update_job_status(
        db_session, 
        job_id, 
        "completed",
        current_test_id="test-1",
        current_turn=2,
        completed_tests=3,
        failed_tests=1,
        error="Test error"
    )
    
    assert updated_job is not None
    assert updated_job.status == "completed"
    assert updated_job.current_test_id == "test-1"
    assert updated_job.current_turn == 2
    assert updated_job.completed_tests == 3
    assert updated_job.failed_tests == 1
    assert updated_job.error == "Test error"
    assert updated_job.progress == (3 + 1) / 5 * 100  # (completed + failed) / total * 100
    assert updated_job.completed_at is not None
    
    # Test updating a non-existent job
    non_existent_job = job_repository.update_job_status(db_session, "non-existent-id", "completed")
    assert non_existent_job is None


def test_test_result_operations(db_session, job_repository):
    """Test test result operations."""
    # Create a job
    job_id = str(uuid.uuid4())
    job = Job(
        id=job_id,
        batch_id="test-batch",
        status="running",
        started_at=datetime.utcnow(),
        total_tests=1
    )
    db_session.add(job)
    db_session.commit()
    
    # Create a test result
    test_id = "test-1"
    test_result = job_repository.create_test_result(db_session, job_id, test_id)
    
    assert test_result is not None
    assert test_result.job_id == job_id
    assert test_result.test_id == test_id
    assert test_result.status == "running"
    
    # Update test result
    updated_test_result = job_repository.update_test_result(
        db_session,
        test_result.id,
        "completed",
        total_validations=10,
        passed_validations=8,
        failed_validations=2,
        avg_response_time=1.5,
        error=None
    )
    
    assert updated_test_result is not None
    assert updated_test_result.status == "completed"
    assert updated_test_result.total_validations == 10
    assert updated_test_result.passed_validations == 8
    assert updated_test_result.failed_validations == 2
    assert updated_test_result.avg_response_time == 1.5
    assert updated_test_result.pass_rate == 80.0  # 8/10 * 100
    assert updated_test_result.completed_at is not None


def test_turn_and_validation_results(db_session, job_repository):
    """Test turn and validation result operations."""
    # Create a job and test result
    job_id = str(uuid.uuid4())
    job = Job(
        id=job_id,
        batch_id="test-batch",
        status="running",
        started_at=datetime.utcnow(),
        total_tests=1
    )
    db_session.add(job)
    db_session.commit()
    
    test_result = job_repository.create_test_result(db_session, job_id, "test-1")
    
    # Create a turn result
    turn_result = job_repository.create_turn_result(
        db_session,
        test_result.id,
        "turn-1",
        1,
        "User input",
        "Agent response",
        "Scraped content",
        500  # response time in ms
    )
    
    assert turn_result is not None
    assert turn_result.test_result_id == test_result.id
    assert turn_result.turn_id == "turn-1"
    assert turn_result.order == 1
    assert turn_result.user_input == "User input"
    assert turn_result.agent_response == "Agent response"
    assert turn_result.scraped_content == "Scraped content"
    assert turn_result.response_time_ms == 500
    
    # Create validation results
    validation_result1 = job_repository.create_validation_result(
        db_session,
        turn_result.id,
        "validation-1",
        "contains",
        True,
        1.0,
        {"details": "Validation details"}
    )
    
    validation_result2 = job_repository.create_validation_result(
        db_session,
        turn_result.id,
        "validation-2",
        "regex",
        False,
        0.0,
        {"details": "Failed validation"}
    )
    
    assert validation_result1 is not None
    assert validation_result1.turn_result_id == turn_result.id
    assert validation_result1.validation_id == "validation-1"
    assert validation_result1.is_passed is True
    
    assert validation_result2 is not None
    assert validation_result2.is_passed is False
    
    # Check that turn result validation counts were updated
    turn_result = db_session.query(TurnResult).filter(TurnResult.id == turn_result.id).first()
    assert turn_result.validations_total == 2
    assert turn_result.validations_passed == 1
    assert turn_result.validations_failed == 1


def test_get_batch_status(db_session, job_repository):
    """Test getting batch status."""
    # Create a job
    job_id = str(uuid.uuid4())
    job = Job(
        id=job_id,
        batch_id="test-batch",
        status="running",
        started_at=datetime.utcnow(),
        total_tests=5,
        completed_tests=2,
        failed_tests=1,
        current_test_id="test-3",
        current_turn=2,
        progress=60.0
    )
    db_session.add(job)
    db_session.commit()
    
    # Get batch status
    batch_status = job_repository.get_batch_status(db_session, job_id)
    
    assert batch_status is not None
    assert batch_status.job_id == job_id
    assert batch_status.batch_id == "test-batch"
    assert batch_status.status == "running"
    assert batch_status.total_tests == 5
    assert batch_status.completed_tests == 2
    assert batch_status.failed_tests == 1
    assert batch_status.current_test_id == "test-3"
    assert batch_status.current_turn == 2
    assert batch_status.progress == 60.0


def test_get_batch_results(db_session, job_repository):
    """Test getting batch results."""
    # Create a complete job with test, turn, and validation results
    job_id = str(uuid.uuid4())
    batch_id = "test-batch"
    
    # Create job
    job = Job(
        id=job_id,
        batch_id=batch_id,
        status="completed",
        started_at=datetime.utcnow(),
        completed_at=datetime.utcnow(),
        total_tests=1,
        completed_tests=1
    )
    db_session.add(job)
    db_session.commit()
    
    # Create test result
    test_result = TestResult(
        job_id=job_id,
        test_id="test-1",
        status="completed",
        started_at=datetime.utcnow(),
        completed_at=datetime.utcnow(),
        total_validations=2,
        passed_validations=1,
        failed_validations=1,
        pass_rate=50.0,
        avg_response_time=750.0
    )
    db_session.add(test_result)
    db_session.commit()
    
    # Create turn result
    turn_result = TurnResult(
        test_result_id=test_result.id,
        turn_id="turn-1",
        order=1,
        user_input="User input",
        agent_response="Agent response",
        scraped_content="Scraped content",
        response_time_ms=750,
        validations_total=2,
        validations_passed=1,
        validations_failed=1
    )
    db_session.add(turn_result)
    db_session.commit()
    
    # Create validation results
    validation_result1 = ValidationResult(
        turn_result_id=turn_result.id,
        validation_id="validation-1",
        validation_type="contains",
        is_passed=True,
        score=1.0,
        details={"details": "Validation details"}
    )
    
    validation_result2 = ValidationResult(
        turn_result_id=turn_result.id,
        validation_id="validation-2",
        validation_type="regex",
        is_passed=False,
        score=0.0,
        details={"details": "Failed validation"}
    )
    
    db_session.add(validation_result1)
    db_session.add(validation_result2)
    db_session.commit()
    
    # Get batch results with scraped content
    batch_results = job_repository.get_batch_results(db_session, job_id, include_scraped_content=True)
    
    assert batch_results is not None
    assert batch_results.job_id == job_id
    assert batch_results.batch_id == batch_id
    assert batch_results.status == "completed"
    assert batch_results.total_tests == 1
    assert batch_results.completed_tests == 1
    
    assert len(batch_results.test_results) == 1
    assert batch_results.test_results[0].test_id == "test-1"
    assert batch_results.test_results[0].status == "completed"
    assert batch_results.test_results[0].total_validations == 2
    assert batch_results.test_results[0].passed_validations == 1
    assert batch_results.test_results[0].pass_rate == 50.0
    
    assert len(batch_results.test_results[0].turn_results) == 1
    assert batch_results.test_results[0].turn_results[0].turn_id == "turn-1"
    assert batch_results.test_results[0].turn_results[0].user_input == "User input"
    assert batch_results.test_results[0].turn_results[0].agent_response == "Agent response"
    assert batch_results.test_results[0].turn_results[0].scraped_content == "Scraped content"
    
    assert len(batch_results.test_results[0].turn_results[0].validation_results) == 2
    
    # Get batch results without scraped content
    batch_results = job_repository.get_batch_results(db_session, job_id, include_scraped_content=False)
    assert batch_results.test_results[0].turn_results[0].scraped_content is None