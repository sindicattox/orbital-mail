from fastapi import APIRouter
from fastapi.responses import JSONResponse

from core.database import check_database_health
from core.settings import get_settings

router = APIRouter(tags=["Health"])


@router.get("/health")
def health() -> dict:
    settings = get_settings()
    return {
        "status": "ok",
        "service": settings.app_service,
        "environment": settings.app_env,
    }


@router.get("/health/db")
def health_db() -> JSONResponse:
    settings = get_settings()
    result = check_database_health()
    database = {
        "provider": result["provider"],
        "status": "ok" if result["ok"] else "unavailable",
        "latency_ms": result["latency_ms"],
    }
    if not result["ok"]:
        database["error_type"] = result["error_type"]
    return JSONResponse(
        status_code=200 if result["ok"] else 503,
        content={
            "status": "ok" if result["ok"] else "unavailable",
            "service": settings.app_service,
            "environment": settings.app_env,
            "database": database,
        },
        headers={} if result["ok"] else {"Retry-After": "2"},
    )
