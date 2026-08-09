from pathlib import Path

import pytest
from pydantic import ValidationError

from core.settings import Settings

ROOT = Path(__file__).resolve().parents[1]


def _production_settings(
    upload_url: str,
    public_url: str = "https://admin.sindicatto.com/orbital-mail",
) -> Settings:
    return Settings(
        _env_file=None,
        APP_ENV="production",
        APP_CORS_ORIGINS="https://admin.sindicatto.com",
        AUTH_MODE="remote",
        AUTH_CONTEXT_URL="http://127.0.0.1:8001/auth/context/module",
        DB_PROVIDER="oracle",
        ORACLE_USER="WKSP_SINDICATTO",
        ORACLE_PASSWORD="secret",
        ORACLE_CONNECT_STRING="sindicatto_tp",
        ORACLE_WALLET_DIR="/home/ubuntu/.oracle/Wallet_sindicatto",
        ORACLE_CURRENT_SCHEMA="WKSP_SINDICATTO",
        EMAIL_UPLOAD_PUBLIC_URL=upload_url,
        MAIL_PUBLIC_URL=public_url,
        MAIL_UNSUBSCRIBE_SECRET="stable-production-secret",
    )


def test_local_public_upload_url_uses_canonical_api_route():
    settings = Settings(
        _env_file=None,
        APP_ENV="development",
        EMAIL_UPLOAD_PUBLIC_URL="https://admin.localhost/orbital-mail/api/mail/uploads/",
        MAIL_PUBLIC_URL="https://admin.localhost/orbital-mail",
    )

    assert settings.mail_public_upload_url == "https://admin.localhost/orbital-mail/api/mail/uploads"
    assert settings.mail_public_url == "https://admin.localhost/orbital-mail"


def test_wrong_uploads_mail_path_is_rejected_before_api_starts():
    with pytest.raises(ValidationError, match=r"Use exatamente /orbital-mail/api/mail/uploads"):
        Settings(
            _env_file=None,
            APP_ENV="development",
            EMAIL_UPLOAD_PUBLIC_URL="http://127.0.0.1:8106/uploads/mail",
            MAIL_PUBLIC_URL="http://127.0.0.1:8106/orbital-mail",
        )


def test_production_accepts_public_https_canonical_route():
    settings = _production_settings(
        "https://admin.sindicatto.com/orbital-mail/api/mail/uploads"
    )

    assert settings.mail_public_upload_url == (
        "https://admin.sindicatto.com/orbital-mail/api/mail/uploads"
    )


def test_production_rejects_local_gateway_domain():
    with pytest.raises(ValidationError, match="EMAIL_UPLOAD_PUBLIC_URL sem endereço local"):
        _production_settings(
            "https://admin.localhost/orbital-mail/api/mail/uploads",
            "https://admin.localhost/orbital-mail",
        )


def test_upload_and_unsubscribe_must_share_protocol_and_domain():
    with pytest.raises(ValidationError, match="mesmo protocolo e domínio"):
        _production_settings(
            "https://cdn.sindicatto.com/orbital-mail/api/mail/uploads",
            "https://admin.sindicatto.com/orbital-mail",
        )


def test_production_requires_stable_unsubscribe_secret():
    with pytest.raises(ValidationError, match="MAIL_UNSUBSCRIBE_SECRET"):
        Settings(
            _env_file=None,
            APP_ENV="production",
            AUTH_MODE="remote",
            AUTH_CONTEXT_URL="http://127.0.0.1:8001/auth/context/module",
            DB_PROVIDER="oracle",
            ORACLE_USER="WKSP_SINDICATTO",
            ORACLE_PASSWORD="secret",
            ORACLE_CONNECT_STRING="sindicatto_tp",
            ORACLE_WALLET_DIR="/home/ubuntu/.oracle/Wallet_sindicatto",
            ORACLE_CURRENT_SCHEMA="WKSP_SINDICATTO",
            EMAIL_UPLOAD_PUBLIC_URL="https://admin.sindicatto.com/orbital-mail/api/mail/uploads",
            MAIL_PUBLIC_URL="https://admin.sindicatto.com/orbital-mail",
            MAIL_UNSUBSCRIBE_SECRET="",
        )


def test_remote_public_image_smoke_script_exists_and_is_executable():
    script = ROOT / "deploy/remote/test-public-image.sh"
    content = script.read_text()

    assert script.stat().st_mode & 0o111
    assert "Nginx/HTTPS -> API -> storage do tenant" in content
    assert "cmp -s" in content
    assert "HTTP_CODE" in content


def test_canonical_public_route_serves_tenant_file_and_legacy_wrong_route_is_404(
    tmp_path,
    monkeypatch,
):
    from fastapi import FastAPI
    from fastapi.testclient import TestClient

    from mail import images
    from mail.image_storage import tenant_upload_dir

    settings = Settings(
        _env_file=None,
        APP_ENV="development",
        EMAIL_UPLOAD_DIR=str(tmp_path / "tenants/{tenant}/media/email_campaign"),
        EMAIL_UPLOAD_PUBLIC_URL="http://testserver/orbital-mail/api/mail/uploads",
        MAIL_PUBLIC_URL="http://testserver/orbital-mail",
    )
    monkeypatch.setattr(images, "settings", settings)

    filename = "a" * 32 + ".png"
    directory = tenant_upload_dir(settings, "anpprev")
    directory.mkdir(parents=True)
    payload = b"\\x89PNG\\r\\n\\x1a\\npublic-image-test"
    (directory / filename).write_bytes(payload)

    app = FastAPI()
    app.include_router(images.router, prefix="/api/mail")
    client = TestClient(app)

    response = client.get(f"/api/mail/uploads/anpprev/{filename}")
    assert response.status_code == 200
    assert response.content == payload
    assert response.headers["content-type"] == "image/png"
    assert client.get(f"/uploads/mail/anpprev/{filename}").status_code == 404
