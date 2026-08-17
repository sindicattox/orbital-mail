from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from core.errors import register_error_handlers
from core.settings import get_settings
from mail.router import router as mail_router
from mail.images import router as mail_images_router
from mail.delivery_test_service import router as mail_test_send_router
from mail.test_loop_service import router as mail_test_loop_router
from mail.settings_router import router as mail_settings_router
from mail.unsubscribe import router as mail_unsubscribe_router
from routes.auth import router as auth_router
from routes.health import router as health_router

settings = get_settings()
_public_docs = settings.app_env != "production"
app = FastAPI(
    title=settings.app_name,
    version="1.0.0",
    docs_url="/docs" if _public_docs else None,
    redoc_url="/redoc" if _public_docs else None,
    openapi_url="/openapi.json" if _public_docs else None,
)
register_error_handlers(app)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(health_router, prefix="/api")
app.include_router(auth_router, prefix="/api/mail")
app.include_router(mail_router, prefix="/api/mail")
app.include_router(mail_images_router, prefix="/api/mail")
app.include_router(mail_test_send_router, prefix="/api/mail")
app.include_router(mail_test_loop_router, prefix="/api/mail")
app.include_router(mail_settings_router, prefix="/api/mail")
app.include_router(mail_unsubscribe_router, prefix="/api/mail")
