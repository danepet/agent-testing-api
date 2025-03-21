from fastapi import APIRouter, Response
from app.core.metrics import get_metrics, get_metrics_content_type

router = APIRouter()


@router.get("/metrics", include_in_schema=False)
async def metrics():
    """
    Get Prometheus metrics.
    """
    return Response(
        content=get_metrics(),
        media_type=get_metrics_content_type()
    )


@router.get("/health")
async def health():
    """
    Health check endpoint.
    """
    return {"status": "ok"}