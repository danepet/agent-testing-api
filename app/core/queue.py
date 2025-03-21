import asyncio
import logging
from typing import Dict, List, Any, Optional, Callable, Awaitable
import uuid
from datetime import datetime

from app.core.config import settings
from app.core.metrics import update_active_jobs, update_queue_size

# Configure logging
logger = logging.getLogger(__name__)

class TaskQueue:
    """
    Task queue for managing asynchronous job execution.
    """
    
    def __init__(self):
        self.queue = asyncio.Queue()
        self.active_jobs: Dict[str, Dict[str, Any]] = {}
        self.workers: List[asyncio.Task] = []
        self.max_workers = settings.MAX_CONCURRENT_JOBS
        self.running = False
    
    async def enqueue_job(self, job_id: str, task: Callable[[str, Any], Awaitable[None]], *args, **kwargs) -> None:
        """
        Add a job to the queue.
        
        Args:
            job_id: Job identifier
            task: Async function to execute
            *args: Arguments for the task
            **kwargs: Keyword arguments for the task
        """
        logger.info(f"Enqueueing job: {job_id}")
        
        # Add job to queue
        await self.queue.put((job_id, task, args, kwargs))
        
        # Update metrics
        update_queue_size(self.queue.qsize())
        
        # Ensure workers are running
        self._ensure_workers()
    
    def _ensure_workers(self) -> None:
        """
        Ensure that worker tasks are running.
        """
        if not self.running:
            return
            
        # Start new workers if needed
        while len(self.workers) < self.max_workers:
            worker = asyncio.create_task(self._worker())
            self.workers.append(worker)
            logger.debug(f"Started new worker, total workers: {len(self.workers)}")
    
    async def _worker(self) -> None:
        """
        Worker task that processes jobs from the queue.
        """
        worker_id = str(uuid.uuid4())
        logger.debug(f"Worker {worker_id} started")
        
        try:
            while self.running:
                try:
                    # Get job from queue with timeout
                    try:
                        job_id, task, args, kwargs = await asyncio.wait_for(
                            self.queue.get(), 
                            timeout=5.0
                        )
                    except asyncio.TimeoutError:
                        continue
                    
                    # Update metrics
                    update_queue_size(self.queue.qsize())
                    
                    # Track active job
                    self.active_jobs[job_id] = {
                        "started_at": datetime.utcnow().isoformat(),
                        "worker_id": worker_id
                    }
                    update_active_jobs(len(self.active_jobs))
                    
                    logger.info(f"Worker {worker_id} processing job {job_id}")
                    
                    # Execute task
                    try:
                        await task(job_id, *args, **kwargs)
                        logger.info(f"Worker {worker_id} completed job {job_id}")
                    except Exception as e:
                        logger.error(f"Worker {worker_id} failed job {job_id}: {str(e)}", exc_info=True)
                    
                    # Remove from active jobs
                    if job_id in self.active_jobs:
                        del self.active_jobs[job_id]
                    update_active_jobs(len(self.active_jobs))
                    
                    # Mark task as done
                    self.queue.task_done()
                    
                except Exception as e:
                    logger.error(f"Worker {worker_id} error: {str(e)}", exc_info=True)
                    
        finally:
            logger.debug(f"Worker {worker_id} stopped")
            # Remove this worker from the list
            if asyncio.current_task() in self.workers:
                self.workers.remove(asyncio.current_task())
    
    async def start(self) -> None:
        """
        Start the task queue.
        """
        if self.running:
            return
            
        logger.info("Starting task queue")
        self.running = True
        self._ensure_workers()
    
    async def stop(self) -> None:
        """
        Stop the task queue.
        """
        if not self.running:
            return
            
        logger.info("Stopping task queue")
        self.running = False
        
        # Wait for all workers to complete
        if self.workers:
            await asyncio.gather(*self.workers, return_exceptions=True)
        
        # Clear the queue
        while not self.queue.empty():
            try:
                self.queue.get_nowait()
                self.queue.task_done()
            except asyncio.QueueEmpty:
                break
        
        # Update metrics
        update_queue_size(0)
        update_active_jobs(0)
        
        logger.info("Task queue stopped")
    
    def get_status(self) -> Dict[str, Any]:
        """
        Get the status of the task queue.
        
        Returns:
            Dict[str, Any]: Queue status
        """
        return {
            "running": self.running,
            "workers": len(self.workers),
            "queue_size": self.queue.qsize(),
            "active_jobs": len(self.active_jobs),
            "active_job_ids": list(self.active_jobs.keys())
        }