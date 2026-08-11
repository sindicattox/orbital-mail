from fastapi import APIRouter
from fastapi.responses import JSONResponse

from core.database import check_database_health, get_session_factory
from core.settings import get_settings
from mail.delivery_worker_service import MailDeliveryWorkerService, MailSendWorkerSchemaMissingError

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


@router.get("/health/worker")
def health_worker() -> JSONResponse:
    settings = get_settings()
    db = None
    try:
        db = get_session_factory()()
        MailDeliveryWorkerService(db, settings).check_readiness()
        ok = True
        error_type = None
        detail = None
    except Exception as error:
        ok = False
        error_type = type(error).__name__
        detail = str(error) if isinstance(error, MailSendWorkerSchemaMissingError) else None
    finally:
        if db is not None:
            db.close()

    worker = {
        "status": "ok" if ok else "unavailable",
        "send_enabled": settings.mail_send_enabled,
        "provider": settings.mail_provider,
    }
    if error_type:
        worker["error_type"] = error_type
    if detail:
        worker["detail"] = detail
    return JSONResponse(
        status_code=200 if ok else 503,
        content={
            "status": "ok" if ok else "unavailable",
            "service": settings.app_service,
            "environment": settings.app_env,
            "worker": worker,
        },
        headers={} if ok else {"Retry-After": "2"},
    )
