from typing import Dict, List, Any, Optional
import asyncio
import time
import logging
from datetime import datetime
import json

from sqlalchemy.orm import Session

from app.db.repositories.job_repository import JobRepository
from app.models.batch import BatchStatus
from app.models.results import BatchResults, TestResult, TurnResult, ValidationResult
from app.services.agent import AgentService
from app.services.validation import ValidationService
from app.services.scraper import ScraperService
from app.db.session import SessionLocal
from app.core.metrics import record_test_execution, record_validation_execution, record_api_latency

# Configure logging
logger = logging.getLogger(__name__)


class ExecutionService:
    def __init__(self):
        self.agent_service = AgentService()
        self.validation_service = ValidationService()
        self.scraper_service = ScraperService()
        self.job_repository = JobRepository()
    
    async def execute_batch(self, job_id: str, batch_id: str, tests: List[Dict[str, Any]]) -> None:
        """
        Execute a batch of tests asynchronously.
        """
        # Create a new database session for this async task
        db = SessionLocal()
        
        try:
            # Initialize job in the database
            logger.info(f"Starting batch execution: job_id={job_id}, batch_id={batch_id}, tests={len(tests)}")
            self.job_repository.create_job(db, job_id, batch_id, len(tests))
            self.job_repository.update_job_status(db, job_id, "running")
            
            for test in tests:
                test_id = test.test_id
                
                # Update job status
                logger.info(f"Processing test: job_id={job_id}, test_id={test_id}")
                self.job_repository.update_job_status(
                    db, 
                    job_id, 
                    "running",
                    current_test_id=test_id,
                    current_turn=0
                )
                
                # Initialize test result
                test_result = self.job_repository.create_test_result(db, job_id, test_id)
                
                try:
                    # Start agent session
                    session_id = await self.agent_service.start_session(
                        test_id, test.credentials
                    )
                    
                    # Record test execution start in metrics
                    record_test_execution(test_id, "started")
                    
                    # Process each turn
                    response_times = []
                    for turn in test.turns:
                        # Update job status
                        self.job_repository.update_job_status(
                            db, 
                            job_id, 
                            "running",
                            current_turn=turn["order"]
                        )
                        
                        # Send message to agent
                        start_time = time.time()
                        
                        # Add retry logic for agent communication
                        agent_response = None
                        max_retries = 3
                        retry_count = 0
                        
                        while retry_count < max_retries:
                            try:
                                # Record API call latency
                                with record_api_latency("agent_message"):
                                    agent_response = await self.agent_service.send_message(
                                        session_id, turn["user_input"]
                                    )
                                break
                            except Exception as e:
                                retry_count += 1
                                logger.warning(f"Retry {retry_count}/{max_retries} - Error sending message to agent: {str(e)}")
                                if retry_count >= max_retries:
                                    raise
                                await asyncio.sleep(1)  # Wait before retrying
                        
                        response_time_ms = int((time.time() - start_time) * 1000)
                        response_times.append(response_time_ms)
                        
                        # Extract URLs and scrape content if any
                        scraped_content = None
                        urls = self.scraper_service.extract_urls(agent_response)
                        if urls:
                            try:
                                with record_api_latency("web_scraping"):
                                    scraped_content = await self.scraper_service.scrape_urls(
                                        urls, test.get("config", {}).get("html_selector")
                                    )
                            except Exception as e:
                                logger.warning(f"Error scraping content: {str(e)}")
                                
                        # Create turn result in database
                        turn_result = self.job_repository.create_turn_result(
                            db,
                            test_result.id,
                            turn["turn_id"],
                            turn["order"],
                            turn["user_input"],
                            agent_response,
                            scraped_content,
                            response_time_ms
                        )
                        
                        # Process validations
                        validation_results = []
                        passed_validations = 0
                        for validation in turn["validations"]:
                            # Update validation parameters with scraped content if needed
                            params = self._update_validation_params(
                                validation["validation_type"],
                                validation["validation_parameters"],
                                scraped_content
                            )
                            
                            # Validate the response with retry logic
                            validation_result = None
                            retry_count = 0
                            
                            while retry_count < max_retries:
                                try:
                                    # Record validation execution in metrics
                                    with record_api_latency("validation"):
                                        validation_result = await self.validation_service.validate(
                                            validation["validation_type"],
                                            agent_response,
                                            params
                                        )
                                    break
                                except Exception as e:
                                    retry_count += 1
                                    logger.warning(f"Retry {retry_count}/{max_retries} - Error validating response: {str(e)}")
                                    if retry_count >= max_retries:
                                        # Create a failure result
                                        validation_result = {
                                            "passed": False,
                                            "score": 0.0,
                                            "details": f"Validation failed after {max_retries} retries: {str(e)}"
                                        }
                                    else:
                                        await asyncio.sleep(1)  # Wait before retrying
                            
                            is_passed = validation_result.get("passed", False)
                            if is_passed:
                                passed_validations += 1
                                
                            # Record validation result in database
                            self.job_repository.create_validation_result(
                                db,
                                turn_result.id,
                                validation["validation_id"],
                                validation["validation_type"],
                                is_passed,
                                validation_result.get("score"),
                                validation_result
                            )
                            
                            # Record metric for validation
                            record_validation_execution(
                                validation["validation_type"], 
                                "success" if is_passed else "failure"
                            )
                    
                    # End agent session
                    await self.agent_service.end_session(session_id)
                    
                    # Calculate average response time
                    avg_response_time = sum(response_times) / len(response_times) if response_times else 0
                    
                    # Update test result
                    self.job_repository.update_test_result(
                        db,
                        test_result.id,
                        "completed",
                        avg_response_time=avg_response_time
                    )
                    
                    # Record test execution completion in metrics
                    record_test_execution(test_id, "completed")
                    
                    # Update job completed tests count
                    completed_tests = self.job_repository.get_job(db, job_id).completed_tests or 0
                    self.job_repository.update_job_status(
                        db,
                        job_id,
                        "running",
                        completed_tests=completed_tests + 1
                    )
                    
                except Exception as e:
                    # Log the error
                    logger.error(f"Error executing test {test_id}: {str(e)}", exc_info=True)
                    
                    # Mark test as failed
                    self.job_repository.update_test_result(
                        db,
                        test_result.id,
                        "failed",
                        error=str(e)
                    )
                    
                    # Record test execution failure in metrics
                    record_test_execution(test_id, "failed")
                    
                    # Update job failed tests count
                    failed_tests = self.job_repository.get_job(db, job_id).failed_tests or 0
                    self.job_repository.update_job_status(
                        db,
                        job_id,
                        "running",
                        failed_tests=failed_tests + 1
                    )
            
            # Mark job as completed
            self.job_repository.update_job_status(db, job_id, "completed")
            logger.info(f"Batch execution completed: job_id={job_id}")
            
        except Exception as e:
            # Log the error
            logger.error(f"Error executing batch {job_id}: {str(e)}", exc_info=True)
            
            # Mark job as failed
            self.job_repository.update_job_status(db, job_id, "failed", error=str(e))
        
        finally:
            # Close the database session
            db.close()
    
    def get_batch_status(self, job_id: str) -> Optional[BatchStatus]:
        """
        Get the status of a batch execution.
        """
        with SessionLocal() as db:
            return self.job_repository.get_batch_status(db, job_id)
    
    def get_batch_results(self, job_id: str, include_scraped_content: bool = False) -> Optional[BatchResults]:
        """
        Get the complete results for a batch execution.
        """
        with SessionLocal() as db:
            return self.job_repository.get_batch_results(db, job_id, include_scraped_content)
    
    def _update_validation_params(
        self, 
        validation_type: str, 
        parameters: Dict[str, Any], 
        scraped_content: Optional[str]
    ) -> Dict[str, Any]:
        """
        Update validation parameters with scraped content if needed.
        """
        if not scraped_content:
            return parameters
        
        params = parameters.copy()
        
        # Add scraped content to context-based validations
        if validation_type in ["contextual_relevancy", "faithfulness"]:
            if "context" in params:
                params["context"] = f"{params['context']}\n\n{scraped_content}"
            else:
                params["context"] = scraped_content
        
        return params