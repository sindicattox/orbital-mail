from pathlib import Path

import pytest
from pydantic import ValidationError

from core.settings import Settings

ROOT = Path(__file__).resolve().parents[1]


def _production_settings(public_url: str) -> Settings:
    return Settings(
        _env_file=None,
        app_env="production",
        cors_origins=["https://email.anpprev.org"],
        auth_mode="remote",
        auth_authorize_url="https://admin.anpprev.org/auth/sso/authorize",
        auth_token_url="http://127.0.0.1:8001/auth/sso/token",
        auth_client_id="email-app",
        auth_client_secret="production-client-secret",
        auth_redirect_uri="https://email.anpprev.org/api/mail/auth/callback",
        auth_web_url="https://email.anpprev.org/",
        auth_session_secret="production-session-secret-with-32-chars",
        auth_cookie_secure=True,
        oracle_user="WKSP_SINDICATTO",
        oracle_password="secret",
        oracle_connect_string="sindicatto_tp",
        oracle_wallet_remote_dir="/home/ubuntu/.oracle/Wallet_sindicatto",
        oracle_current_schema="WKSP_SINDICATTO",
        mail_public_upload_url=public_url,
    )


def test_local_public_upload_url_uses_canonical_api_route():
    settings = Settings(
        _env_file=None,
        mail_public_upload_url="http://127.0.0.1:8104/api/mail/uploads/",
    )

    assert settings.mail_public_upload_url == "http://127.0.0.1:8104/api/mail/uploads"


def test_wrong_uploads_mail_path_is_rejected_before_api_starts():
    with pytest.raises(ValidationError, match=r"Use exatamente /api/mail/uploads"):
        Settings(
            _env_file=None,
            mail_public_upload_url="http://127.0.0.1:8104/uploads/mail",
        )


def test_production_accepts_public_https_canonical_route():
    settings = _production_settings("https://email.anpprev.org/api/mail/uploads")

    assert settings.mail_public_upload_url == "https://email.anpprev.org/api/mail/uploads"


def test_production_rejects_localhost_even_with_canonical_route():
    with pytest.raises(ValidationError, match="EMAIL_UPLOAD_PUBLIC_URL sem endereço local"):
        _production_settings("https://127.0.0.1/api/mail/uploads")


def test_remote_public_image_smoke_script_exists_and_is_executable():
    script = ROOT / "deploy/remote/test-public-image.sh"
    content = script.read_text()

    assert script.stat().st_mode & 0o111
    assert "Nginx/HTTPS -> API -> storage do tenant" in content
    assert "cmp -s" in content
    assert "HTTP_CODE" in content


def test_canonical_public_route_serves_tenant_file_and_legacy_wrong_route_is_404(tmp_path, monkeypatch):
    from fastapi import FastAPI
    from fastapi.testclient import TestClient

    from mail import images
    from mail.image_storage import tenant_upload_dir

    settings = Settings(
        _env_file=None,
        mail_upload_dir=str(tmp_path / "tenants/{tenant}/media/email_campaign"),
        mail_public_upload_url="http://testserver/api/mail/uploads",
    )
    monkeypatch.setattr(images, "settings", settings)

    filename = "a" * 32 + ".png"
    directory = tenant_upload_dir(settings, "anpprev")
    directory.mkdir(parents=True)
    payload = b"\x89PNG\r\n\x1a\npublic-image-test"
    (directory / filename).write_bytes(payload)

    app = FastAPI()
    app.include_router(images.router, prefix="/api/mail")
    client = TestClient(app)

    response = client.get(f"/api/mail/uploads/anpprev/{filename}")
    assert response.status_code == 200
    assert response.content == payload
    assert response.headers["content-type"] == "image/png"
    assert client.get(f"/uploads/mail/anpprev/{filename}").status_code == 404
