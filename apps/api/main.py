from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from core.errors import register_error_handlers
from core.settings import get_settings
from mail.router import router as mail_router
from mail.images import router as mail_images_router
from mail.delivery_test_service import router as mail_test_send_router
from mail.test_loop_service import router as mail_test_loop_router
from routes.auth import router as auth_router
from routes.health import router as health_router

settings = get_settings()
app = FastAPI(title=settings.app_name, version="1.0.0")
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
