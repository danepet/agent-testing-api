from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import logging

from app.api.v1.router import api_router
from app.core.config import settings
from app.core.errors import add_error_handlers
from app.core.logging import setup_logging
from app.api.middleware import add_middleware
from app.db.models import Base
from app.db.session import engine

# Set up logging first
setup_logging()
logger = logging.getLogger("app")

# Create database tables
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="AI Agent Testing API",
    description="API for testing AI Agents with automated validations",
    version="1.0.0"
)

# Set up CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Add custom middleware
add_middleware(app)

# Add error handlers
add_error_handlers(app)

# Include the API router
app.include_router(api_router, prefix="/api/v1")

# Root endpoint
@app.get("/")
async def root():
    return {"message": "Welcome to the AI Agent Testing API. See /docs for API documentation."}

# Startup event
@app.on_event("startup")
async def startup_event():
    logger.info("Application startup")
    
    # Start the task queue
    from app.core.queue_instance import task_queue
    await task_queue.start()

# Shutdown event
@app.on_event("shutdown")
async def shutdown_event():
    logger.info("Application shutdown")
    
    # Stop the task queue
    from app.core.queue_instance import task_queue
    await task_queue.stop()

if __name__ == "__main__":
    import uvicorn
    logger.info("Starting uvicorn server")
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)