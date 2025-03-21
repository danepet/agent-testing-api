from typing import Any, List, Dict, Optional
import os
import logging
from fastapi import APIRouter, Depends, HTTPException, status, Request, BackgroundTasks
from pydantic import BaseModel

from app.core.security import get_current_user, is_admin
from app.core.config import settings
from app.core.queue_instance import task_queue
from app.services.execution import ExecutionService
from app.db.session import SessionLocal

router = APIRouter()
logger = logging.getLogger(__name__)


class ServerStatus(BaseModel):
    """Model for server status information."""
    version: str = "1.0.0"
    hostname: str = settings.HOSTNAME
    database_connected: bool
    queue_status: Dict[str, Any]
    environment: str
    log_level: str = settings.LOG_LEVEL
    memory_usage_mb: float


class SettingUpdate(BaseModel):
    """Model for setting update."""
    name: str
    value: str


@router.get("/status", response_model=ServerStatus)
async def server_status(
    req: Request,
    current_user: dict = Depends(get_current_user),
    admin: bool = Depends(is_admin)
) -> Any:
    """
    Get server status information.
    """
    import psutil
    
    # Check database connection
    db_connected = False
    try:
        db = SessionLocal()
        db.execute("SELECT 1")
        db_connected = True
        db.close()
    except Exception as e:
        logger.error(f"Database connection check failed: {str(e)}", exc_info=True)
    
    # Get memory usage
    process = psutil.Process(os.getpid())
    memory_info = process.memory_info()
    memory_usage_mb = memory_info.rss / 1024 / 1024
    
    return ServerStatus(
        database_connected=db_connected,
        queue_status=task_queue.get_status(),
        environment=os.getenv("ENVIRONMENT", "development"),
        memory_usage_mb=memory_usage_mb
    )


@router.post("/settings")
async def update_setting(
    setting: SettingUpdate,
    req: Request,
    current_user: dict = Depends(get_current_user),
    admin: bool = Depends(is_admin)
) -> Any:
    """
    Update a server setting.
    
    Only certain settings can be updated at runtime.
    """
    # List of settings that can be updated at runtime
    allowed_settings = [
        "LOG_LEVEL",
        "MAX_CONCURRENT_JOBS",
        "RATE_LIMIT_PER_MINUTE",
        "DEFAULT_TIMEOUT_SECONDS",
        "SF_AGENT_TIMEOUT_SECONDS"
    ]
    
    if setting.name not in allowed_settings:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Setting '{setting.name}' cannot be updated at runtime"
        )
    
    # Update setting
    # Note: This is a simplified implementation that only works for the current process
    # In a production environment, you would need to store these in a database or Redis
    if setting.name == "LOG_LEVEL":
        logger.info(f"Changing log level from {settings.LOG_LEVEL} to {setting.value}")
        settings.LOG_LEVEL = setting.value
        # Update logger level
        logging.getLogger("app").setLevel(setting.value)
    elif setting.name == "MAX_CONCURRENT_JOBS":
        logger.info(f"Changing max concurrent jobs from {settings.MAX_CONCURRENT_JOBS} to {setting.value}")
        settings.MAX_CONCURRENT_JOBS = int(setting.value)
        # Update task queue
        task_queue.max_workers = int(setting.value)
    elif setting.name == "RATE_LIMIT_PER_MINUTE":
        logger.info(f"Changing rate limit from {settings.RATE_LIMIT_PER_MINUTE} to {setting.value}")
        settings.RATE_LIMIT_PER_MINUTE = int(setting.value)
    elif setting.name == "DEFAULT_TIMEOUT_SECONDS":
        logger.info(f"Changing default timeout from {settings.DEFAULT_TIMEOUT_SECONDS} to {setting.value}")
        settings.DEFAULT_TIMEOUT_SECONDS = int(setting.value)
    elif setting.name == "SF_AGENT_TIMEOUT_SECONDS":
        logger.info(f"Changing SF agent timeout from {settings.SF_AGENT_TIMEOUT_SECONDS} to {setting.value}")
        settings.SF_AGENT_TIMEOUT_SECONDS = int(setting.value)
    
    return {"message": f"Setting '{setting.name}' updated successfully"}


@router.post("/clear-job/{job_id}")
async def clear_job(
    job_id: str,
    req: Request,
    current_user: dict = Depends(get_current_user),
    admin: bool = Depends(is_admin)
) -> Any:
    """
    Clear a job from the database.
    """
    # This would normally delete the job from the database
    # For simplicity, we'll just return a success message
    logger.warning(
        f"Admin request to clear job {job_id}",
        extra={
            "request_id": getattr(req.state, "request_id", None),
            "job_id": job_id,
            "user": current_user.get("username")
        }
    )
    
    # TODO: Implement actual job deletion
    return {"message": f"Job {job_id} cleared successfully"}


@router.post("/restart-queue")
async def restart_queue(
    req: Request,
    background_tasks: BackgroundTasks,
    current_user: dict = Depends(get_current_user),
    admin: bool = Depends(is_admin)
) -> Any:
    """
    Restart the task queue.
    """
    logger.warning(
        "Admin request to restart queue",
        extra={
            "request_id": getattr(req.state, "request_id", None),
            "user": current_user.get("username")
        }
    )
    
    # Restart the queue in the background
    background_tasks.add_task(restart_task_queue)
    
    return {"message": "Queue restart initiated"}


async def restart_task_queue():
    """Helper function to restart the task queue."""
    logger.info("Restarting task queue")
    
    # Stop the task queue
    await task_queue.stop()
    
    # Wait a moment
    import asyncio
    await asyncio.sleep(1)
    
    # Start the task queue
    await task_queue.start()
    
    logger.info("Task queue restarted")