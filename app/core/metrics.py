import time
import logging
from contextlib import contextmanager
from prometheus_client import Counter, Histogram, Gauge, generate_latest, CONTENT_TYPE_LATEST

# Configure logging
logger = logging.getLogger(__name__)

# Define Prometheus metrics
TEST_EXECUTIONS = Counter(
    'ai_agent_test_executions_total',
    'Total number of test executions',
    ['test_id', 'status']
)

VALIDATION_EXECUTIONS = Counter(
    'ai_agent_validation_executions_total',
    'Total number of validation executions',
    ['validation_type', 'status']
)

API_LATENCY = Histogram(
    'ai_agent_api_latency_seconds',
    'Latency of API calls',
    ['endpoint'],
    buckets=(0.1, 0.5, 1.0, 2.5, 5.0, 7.5, 10.0, 15.0, 30.0, 60.0)
)

ACTIVE_JOBS = Gauge(
    'ai_agent_active_jobs',
    'Number of currently active jobs'
)

QUEUE_SIZE = Gauge(
    'ai_agent_queue_size',
    'Number of jobs in the queue'
)

def record_test_execution(test_id: str, status: str) -> None:
    """
    Record a test execution in metrics.
    
    Args:
        test_id: Test identifier
        status: Execution status (started, completed, failed)
    """
    try:
        TEST_EXECUTIONS.labels(test_id=test_id, status=status).inc()
    except Exception as e:
        logger.error(f"Error recording test execution metric: {str(e)}")


def record_validation_execution(validation_type: str, status: str) -> None:
    """
    Record a validation execution in metrics.
    
    Args:
        validation_type: Type of validation
        status: Execution status (success, failure)
    """
    try:
        VALIDATION_EXECUTIONS.labels(validation_type=validation_type, status=status).inc()
    except Exception as e:
        logger.error(f"Error recording validation execution metric: {str(e)}")


@contextmanager
def record_api_latency(endpoint: str):
    """
    Context manager to record API latency.
    
    Args:
        endpoint: API endpoint name
    """
    start_time = time.time()
    try:
        yield
    finally:
        try:
            latency = time.time() - start_time
            API_LATENCY.labels(endpoint=endpoint).observe(latency)
        except Exception as e:
            logger.error(f"Error recording API latency metric: {str(e)}")


def update_active_jobs(count: int) -> None:
    """
    Update the number of active jobs.
    
    Args:
        count: Number of active jobs
    """
    try:
        ACTIVE_JOBS.set(count)
    except Exception as e:
        logger.error(f"Error updating active jobs metric: {str(e)}")


def update_queue_size(size: int) -> None:
    """
    Update the queue size.
    
    Args:
        size: Queue size
    """
    try:
        QUEUE_SIZE.set(size)
    except Exception as e:
        logger.error(f"Error updating queue size metric: {str(e)}")


def get_metrics() -> bytes:
    """
    Get all metrics in Prometheus format.
    
    Returns:
        bytes: Metrics in Prometheus format
    """
    return generate_latest()


def get_metrics_content_type() -> str:
    """
    Get the content type for Prometheus metrics.
    
    Returns:
        str: Content type
    """
    return CONTENT_TYPE_LATEST