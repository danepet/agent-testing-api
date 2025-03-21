from typing import Dict, List, Optional, Any
from datetime import datetime
from sqlalchemy.orm import Session
from sqlalchemy.orm.attributes import flag_modified

from app.db.models import Job, TestResult, TurnResult, ValidationResult
from app.models.batch import BatchStatus
from app.models.results import BatchResults, TestResult as TestResultModel, TurnResult as TurnResultModel, ValidationResult as ValidationResultModel


class JobRepository:
    """Repository for job-related database operations."""
    
    def create_job(self, db: Session, job_id: str, batch_id: str, total_tests: int) -> Job:
        """
        Create a new job in the database.
        
        Args:
            db: Database session
            job_id: Unique job identifier
            batch_id: Batch identifier
            total_tests: Number of tests in the batch
            
        Returns:
            Job: Created job
        """
        job = Job(
            id=job_id,
            batch_id=batch_id,
            status="queued",
            started_at=datetime.utcnow(),
            total_tests=total_tests,
        )
        db.add(job)
        db.commit()
        db.refresh(job)
        return job
    
    def get_job(self, db: Session, job_id: str) -> Optional[Job]:
        """
        Get a job by ID.
        
        Args:
            db: Database session
            job_id: Job identifier
            
        Returns:
            Optional[Job]: Job if found, else None
        """
        return db.query(Job).filter(Job.id == job_id).first()
    
    def update_job_status(
        self, 
        db: Session, 
        job_id: str, 
        status: str,
        current_test_id: Optional[str] = None,
        current_turn: Optional[int] = None,
        completed_tests: Optional[int] = None,
        failed_tests: Optional[int] = None,
        error: Optional[str] = None
    ) -> Optional[Job]:
        """
        Update job status.
        
        Args:
            db: Database session
            job_id: Job identifier
            status: New status
            current_test_id: Current test ID (optional)
            current_turn: Current turn (optional)
            completed_tests: Number of completed tests (optional)
            failed_tests: Number of failed tests (optional)
            error: Error message (optional)
            
        Returns:
            Optional[Job]: Updated job if found, else None
        """
        job = self.get_job(db, job_id)
        if not job:
            return None
        
        job.status = status
        
        if current_test_id is not None:
            job.current_test_id = current_test_id
            
        if current_turn is not None:
            job.current_turn = current_turn
            
        if completed_tests is not None:
            job.completed_tests = completed_tests
            
        if failed_tests is not None:
            job.failed_tests = failed_tests
            
        if error is not None:
            job.error = error
            
        # Update progress
        if job.total_tests > 0:
            total_processed = (job.completed_tests or 0) + (job.failed_tests or 0)
            job.progress = (total_processed / job.total_tests) * 100
            
        # Set completed_at if status is final
        if status in ["completed", "failed"]:
            job.completed_at = datetime.utcnow()
            
        db.commit()
        db.refresh(job)
        return job
    
    def create_test_result(
        self,
        db: Session,
        job_id: str,
        test_id: str,
    ) -> TestResult:
        """
        Create a new test result.
        
        Args:
            db: Database session
            job_id: Job identifier
            test_id: Test identifier
            
        Returns:
            TestResult: Created test result
        """
        test_result = TestResult(
            job_id=job_id,
            test_id=test_id,
            status="running",
            started_at=datetime.utcnow(),
        )
        db.add(test_result)
        db.commit()
        db.refresh(test_result)
        return test_result
    
    def update_test_result(
        self,
        db: Session,
        test_result_id: int,
        status: str,
        total_validations: Optional[int] = None,
        passed_validations: Optional[int] = None,
        failed_validations: Optional[int] = None,
        avg_response_time: Optional[float] = None,
        error: Optional[str] = None,
    ) -> TestResult:
        """
        Update a test result.
        
        Args:
            db: Database session
            test_result_id: Test result identifier
            status: New status
            total_validations: Total number of validations (optional)
            passed_validations: Number of passed validations (optional)
            failed_validations: Number of failed validations (optional)
            avg_response_time: Average response time (optional)
            error: Error message (optional)
            
        Returns:
            TestResult: Updated test result
        """
        test_result = db.query(TestResult).filter(TestResult.id == test_result_id).first()
        if not test_result:
            return None
        
        test_result.status = status
        
        if total_validations is not None:
            test_result.total_validations = total_validations
            
        if passed_validations is not None:
            test_result.passed_validations = passed_validations
            
        if failed_validations is not None:
            test_result.failed_validations = failed_validations
            
        if avg_response_time is not None:
            test_result.avg_response_time = avg_response_time
            
        if error is not None:
            test_result.error = error
            
        # Calculate pass rate
        if test_result.total_validations > 0:
            test_result.pass_rate = (test_result.passed_validations / test_result.total_validations) * 100
            
        # Set completed_at if status is final
        if status in ["completed", "failed"]:
            test_result.completed_at = datetime.utcnow()
            
        db.commit()
        db.refresh(test_result)
        return test_result
    
    def create_turn_result(
        self,
        db: Session,
        test_result_id: int,
        turn_id: str,
        order: int,
        user_input: str,
        agent_response: str,
        scraped_content: Optional[str] = None,
        response_time_ms: int = 0,
    ) -> TurnResult:
        """
        Create a new turn result.
        
        Args:
            db: Database session
            test_result_id: Test result identifier
            turn_id: Turn identifier
            order: Turn order
            user_input: User input
            agent_response: Agent response
            scraped_content: Scraped content (optional)
            response_time_ms: Response time in milliseconds
            
        Returns:
            TurnResult: Created turn result
        """
        turn_result = TurnResult(
            test_result_id=test_result_id,
            turn_id=turn_id,
            order=order,
            user_input=user_input,
            agent_response=agent_response,
            scraped_content=scraped_content,
            response_time_ms=response_time_ms,
        )
        db.add(turn_result)
        db.commit()
        db.refresh(turn_result)
        return turn_result
    
    def create_validation_result(
        self,
        db: Session,
        turn_result_id: int,
        validation_id: str,
        validation_type: str,
        is_passed: bool,
        score: Optional[float] = None,
        details: Optional[Dict[str, Any]] = None,
    ) -> ValidationResult:
        """
        Create a new validation result.
        
        Args:
            db: Database session
            turn_result_id: Turn result identifier
            validation_id: Validation identifier
            validation_type: Validation type
            is_passed: Whether the validation passed
            score: Validation score (optional)
            details: Validation details (optional)
            
        Returns:
            ValidationResult: Created validation result
        """
        validation_result = ValidationResult(
            turn_result_id=turn_result_id,
            validation_id=validation_id,
            validation_type=validation_type,
            is_passed=is_passed,
            score=score,
            details=details,
        )
        db.add(validation_result)
        db.commit()
        
        # Update turn result validation counts
        turn_result = db.query(TurnResult).filter(TurnResult.id == turn_result_id).first()
        if turn_result:
            turn_result.validations_total = db.query(ValidationResult).filter(ValidationResult.turn_result_id == turn_result_id).count()
            turn_result.validations_passed = db.query(ValidationResult).filter(ValidationResult.turn_result_id == turn_result_id, ValidationResult.is_passed == True).count()
            turn_result.validations_failed = turn_result.validations_total - turn_result.validations_passed
            db.commit()
        
        db.refresh(validation_result)
        return validation_result
    
    def get_batch_status(self, db: Session, job_id: str) -> Optional[BatchStatus]:
        """
        Get batch status from the database.
        
        Args:
            db: Database session
            job_id: Job identifier
            
        Returns:
            Optional[BatchStatus]: Batch status if found, else None
        """
        job = self.get_job(db, job_id)
        if not job:
            return None
        
        return BatchStatus(
            job_id=job.id,
            batch_id=job.batch_id,
            status=job.status,
            started_at=job.started_at.isoformat() if job.started_at else None,
            completed_at=job.completed_at.isoformat() if job.completed_at else None,
            progress=job.progress,
            total_tests=job.total_tests,
            completed_tests=job.completed_tests,
            failed_tests=job.failed_tests,
            current_test_id=job.current_test_id,
            current_turn=job.current_turn,
            error=job.error,
        )
    
    def get_batch_results(self, db: Session, job_id: str, include_scraped_content: bool = False) -> Optional[BatchResults]:
        """
        Get batch results from the database.
        
        Args:
            db: Database session
            job_id: Job identifier
            include_scraped_content: Whether to include scraped content
            
        Returns:
            Optional[BatchResults]: Batch results if found, else None
        """
        job = db.query(Job).filter(Job.id == job_id).first()
        if not job:
            return None
        
        # Calculate overall metrics
        test_results_db = db.query(TestResult).filter(TestResult.job_id == job_id).all()
        
        test_results = []
        total_validations = 0
        passed_validations = 0
        total_response_time = 0
        total_turn_count = 0
        
        for test_result_db in test_results_db:
            # Get turn results for this test
            turn_results_db = db.query(TurnResult).filter(TurnResult.test_result_id == test_result_db.id).order_by(TurnResult.order).all()
            
            turn_results = []
            for turn_result_db in turn_results_db:
                # Get validation results for this turn
                validation_results_db = db.query(ValidationResult).filter(ValidationResult.turn_result_id == turn_result_db.id).all()
                
                validation_results = [
                    ValidationResultModel(
                        validation_id=vr.validation_id,
                        validation_type=vr.validation_type,
                        is_passed=vr.is_passed,
                        score=vr.score,
                        details=vr.details,
                    )
                    for vr in validation_results_db
                ]
                
                # Create turn result model
                turn_result = TurnResultModel(
                    turn_id=turn_result_db.turn_id,
                    order=turn_result_db.order,
                    user_input=turn_result_db.user_input,
                    agent_response=turn_result_db.agent_response,
                    scraped_content=turn_result_db.scraped_content if include_scraped_content else None,
                    response_time_ms=turn_result_db.response_time_ms,
                    validations_total=turn_result_db.validations_total,
                    validations_passed=turn_result_db.validations_passed,
                    validations_failed=turn_result_db.validations_failed,
                    validation_results=validation_results,
                )
                
                turn_results.append(turn_result)
                
                # Update metrics
                total_response_time += turn_result_db.response_time_ms
                total_turn_count += 1
            
            # Create test result model
            test_result = TestResultModel(
                test_id=test_result_db.test_id,
                status=test_result_db.status,
                started_at=test_result_db.started_at.isoformat() if test_result_db.started_at else None,
                completed_at=test_result_db.completed_at.isoformat() if test_result_db.completed_at else None,
                error=test_result_db.error,
                total_validations=test_result_db.total_validations,
                passed_validations=test_result_db.passed_validations,
                failed_validations=test_result_db.failed_validations,
                pass_rate=test_result_db.pass_rate,
                avg_response_time=test_result_db.avg_response_time,
                turn_results=turn_results,
            )
            
            test_results.append(test_result)
            
            # Update overall metrics
            total_validations += test_result_db.total_validations
            passed_validations += test_result_db.passed_validations
        
        # Calculate overall metrics
        overall_pass_rate = (passed_validations / total_validations * 100) if total_validations > 0 else 0
        overall_avg_response_time = (total_response_time / total_turn_count) if total_turn_count > 0 else 0
        
        return BatchResults(
            job_id=job.id,
            batch_id=job.batch_id,
            status=job.status,
            started_at=job.started_at.isoformat() if job.started_at else None,
            completed_at=job.completed_at.isoformat() if job.completed_at else None,
            total_tests=job.total_tests,
            completed_tests=job.completed_tests,
            failed_tests=job.failed_tests,
            total_validations=total_validations,
            passed_validations=passed_validations,
            failed_validations=total_validations - passed_validations,
            pass_rate=overall_pass_rate,
            avg_response_time=overall_avg_response_time,
            test_results=test_results,
            error=job.error,
        )