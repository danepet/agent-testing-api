from typing import Dict, List, Any, Optional
import asyncio
import time
from datetime import datetime
import json

from app.models.batch import BatchStatus
from app.models.results import BatchResults, TestResult, TurnResult, ValidationResult
from app.services.agent import AgentService
from app.services.validation import ValidationService
from app.services.scraper import ScraperService


class ExecutionService:
    def __init__(self):
        self.agent_service = AgentService()
        self.validation_service = ValidationService()
        self.scraper_service = ScraperService()
        
        # In-memory storage for job status and results
        # In production, use Redis or a database
        self.jobs: Dict[str, Dict[str, Any]] = {}
    
    async def execute_batch(self, job_id: str, batch_id: str, tests: List[Dict[str, Any]]) -> None:
        """
        Execute a batch of tests asynchronously.
        """
        # Initialize job status
        self.jobs[job_id] = {
            "batch_id": batch_id,
            "status": "running",
            "started_at": datetime.utcnow().isoformat(),
            "completed_at": None,
            "total_tests": len(tests),
            "completed_tests": 0,
            "failed_tests": 0,
            "current_test_id": None,
            "current_turn": None,
            "progress": 0,
            "results": {}
        }
        
        try:
            for test in tests:
                test_id = test["test_id"]
                
                # Update job status
                self.jobs[job_id]["current_test_id"] = test_id
                self.jobs[job_id]["current_turn"] = 0
                
                # Initialize test result
                self.jobs[job_id]["results"][test_id] = {
                    "test_id": test_id,
                    "status": "running",
                    "started_at": datetime.utcnow().isoformat(),
                    "completed_at": None,
                    "turn_results": []
                }
                
                try:
                    # Start agent session
                    session_id = await self.agent_service.start_session(
                        test_id, test["credentials"]
                    )
                    
                    # Process each turn
                    for turn in test["turns"]:
                        # Update job status
                        self.jobs[job_id]["current_turn"] = turn["order"]
                        
                        # Send message to agent
                        start_time = time.time()
                        agent_response = await self.agent_service.send_message(
                            session_id, turn["user_input"]
                        )
                        response_time_ms = int((time.time() - start_time) * 1000)
                        
                        # Extract URLs and scrape content if any
                        scraped_content = None
                        urls = self.scraper_service.extract_urls(agent_response)
                        if urls:
                            scraped_content = await self.scraper_service.scrape_urls(
                                urls, test.get("config", {}).get("html_selector")
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
                            
                            # Validate the response
                            result = await self.validation_service.validate(
                                validation["validation_type"],
                                agent_response,
                                params
                            )
                            
                            if result.get("passed", False):
                                passed_validations += 1
                            
                            validation_results.append({
                                "validation_id": validation["validation_id"],
                                "validation_type": validation["validation_type"],
                                "is_passed": result.get("passed", False),
                                "score": result.get("score"),
                                "details": result
                            })
                        
                        # Record turn result
                        turn_result = {
                            "turn_id": turn["turn_id"],
                            "order": turn["order"],
                            "user_input": turn["user_input"],
                            "agent_response": agent_response,
                            "scraped_content": scraped_content,
                            "response_time_ms": response_time_ms,
                            "validations_total": len(validation_results),
                            "validations_passed": passed_validations,
                            "validations_failed": len(validation_results) - passed_validations,
                            "validation_results": validation_results
                        }
                        
                        self.jobs[job_id]["results"][test_id]["turn_results"].append(turn_result)
                    
                    # End agent session
                    await self.agent_service.end_session(session_id)
                    
                    # Mark test as completed
                    self.jobs[job_id]["results"][test_id]["status"] = "completed"
                    self.jobs[job_id]["results"][test_id]["completed_at"] = datetime.utcnow().isoformat()
                    self.jobs[job_id]["completed_tests"] += 1
                    
                except Exception as e:
                    # Mark test as failed
                    self.jobs[job_id]["results"][test_id]["status"] = "failed"
                    self.jobs[job_id]["results"][test_id]["completed_at"] = datetime.utcnow().isoformat()
                    self.jobs[job_id]["results"][test_id]["error"] = str(e)
                    self.jobs[job_id]["failed_tests"] += 1
                
                # Update progress
                total = self.jobs[job_id]["total_tests"]
                completed = self.jobs[job_id]["completed_tests"] + self.jobs[job_id]["failed_tests"]
                self.jobs[job_id]["progress"] = int((completed / total) * 100) if total > 0 else 0
            
            # Mark job as completed
            self.jobs[job_id]["status"] = "completed"
            self.jobs[job_id]["completed_at"] = datetime.utcnow().isoformat()
            self.jobs[job_id]["current_test_id"] = None
            self.jobs[job_id]["current_turn"] = None
            
        except Exception as e:
            # Mark job as failed
            self.jobs[job_id]["status"] = "failed"
            self.jobs[job_id]["completed_at"] = datetime.utcnow().isoformat()
            self.jobs[job_id]["error"] = str(e)
    
    def get_batch_status(self, job_id: str) -> Optional[BatchStatus]:
        """
        Get the status of a batch execution.
        """
        job = self.jobs.get(job_id)
        if not job:
            return None
        
        return BatchStatus(
            job_id=job_id,
            batch_id=job["batch_id"],
            status=job["status"],
            started_at=job["started_at"],
            completed_at=job["completed_at"],
            progress=job["progress"],
            total_tests=job["total_tests"],
            completed_tests=job["completed_tests"],
            failed_tests=job["failed_tests"],
            current_test_id=job["current_test_id"],
            current_turn=job["current_turn"],
            error=job.get("error")
        )
    
    def get_batch_results(self, job_id: str, include_scraped_content: bool = False) -> Optional[BatchResults]:
        """
        Get the complete results for a batch execution.
        """
        job = self.jobs.get(job_id)
        if not job:
            return None
        
        # Calculate overall metrics
        total_validations = 0
        passed_validations = 0
        failed_validations = 0
        response_times = []
        
        test_results = []
        for test_id, test_data in job["results"].items():
            # Calculate test metrics
            test_validations = 0
            test_passed_validations = 0
            test_response_times = []
            
            turn_results = []
            for turn_data in test_data.get("turn_results", []):
                # Skip scraped content if not requested
                if not include_scraped_content:
                    turn_data = {**turn_data, "scraped_content": None}
                
                test_validations += turn_data.get("validations_total", 0)
                test_passed_validations += turn_data.get("validations_passed", 0)
                
                if turn_data.get("response_time_ms"):
                    test_response_times.append(turn_data["response_time_ms"])
                
                turn_results.append(TurnResult(**turn_data))
            
            # Update overall metrics
            total_validations += test_validations
            passed_validations += test_passed_validations
            failed_validations += test_validations - test_passed_validations
            response_times.extend(test_response_times)
            
            # Calculate test pass rate
            test_pass_rate = 0
            if test_validations > 0:
                test_pass_rate = (test_passed_validations / test_validations) * 100
            
            # Calculate average response time
            avg_response_time = 0
            if test_response_times:
                avg_response_time = sum(test_response_times) / len(test_response_times)
            
            test_results.append(TestResult(
                test_id=test_id,
                status=test_data["status"],
                started_at=test_data["started_at"],
                completed_at=test_data.get("completed_at"),
                error=test_data.get("error"),
                total_validations=test_validations,
                passed_validations=test_passed_validations,
                failed_validations=test_validations - test_passed_validations,
                pass_rate=test_pass_rate,
                avg_response_time=avg_response_time,
                turn_results=turn_results
            ))
        
        # Calculate overall pass rate
        overall_pass_rate = 0
        if total_validations > 0:
            overall_pass_rate = (passed_validations / total_validations) * 100
        
        # Calculate overall average response time
        overall_avg_response_time = 0
        if response_times:
            overall_avg_response_time = sum(response_times) / len(response_times)
        
        return BatchResults(
            job_id=job_id,
            batch_id=job["batch_id"],
            status=job["status"],
            started_at=job["started_at"],
            completed_at=job["completed_at"],
            total_tests=job["total_tests"],
            completed_tests=job["completed_tests"],
            failed_tests=job["failed_tests"],
            total_validations=total_validations,
            passed_validations=passed_validations,
            failed_validations=failed_validations,
            pass_rate=overall_pass_rate,
            avg_response_time=overall_avg_response_time,
            test_results=test_results,
            error=job.get("error")
        )
    
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
