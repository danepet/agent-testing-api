from fastapi import APIRouter
from app.api.v1.endpoints import auth, execution, results

api_router = APIRouter()
api_router.include_router(auth.router, prefix="/auth", tags=["authentication"])
api_router.include_router(execution.router, tags=["execution"])
api_router.include_router(results.router, tags=["results"])
