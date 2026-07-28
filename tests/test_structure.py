from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_required_structure():
    required = [
        "apps/api/main.py",
        "apps/api/core/auth.py",
        "apps/api/core/settings.py",
        "apps/api/mail/router.py",
        "apps/api/mail/schemas.py",
        "apps/web/package.json",
        "apps/web/src/pages/index.astro",
        "apps/web/src/pages/campanhas/index.astro",
        "apps/web/src/pages/campanhas/nova.astro",
        "apps/web/src/pages/dev/components.astro",
        "apps/web/src/components/ApiSandbox.astro",
        "apps/web/src/config/api-url.ts",
        "deploy/local/setup.sh",
        "deploy/local/start.sh",
        "deploy/local/test.sh",
        "deploy/remote/setup-api.sh",
        "deploy/remote/setup-web.sh",
        "deploy/remote/setup.sh",
        "deploy/remote/start-api.sh",
        "deploy/remote/start-web.sh",
        "deploy/remote/start.sh",
        "deploy/remote/test.sh",
        "deploy/remote/target.conf",
        "deploy/remote/systemd/orbital-mail-api.service",
        "deploy/remote/systemd/orbital-mail-web.service",
    ]
    missing = [path for path in required if not (ROOT / path).exists()]
    assert not missing, missing


def test_ports():
    assert "APP_PORT=4104" in (ROOT / "apps/web/.env.example").read_text()
    assert "APP_PORT=8104" in (ROOT / "apps/api/.env.example").read_text()


def test_real_mail_is_disabled_by_default():
    assert "EMAIL_PROVIDER=disabled" in (ROOT / "apps/api/.env.example").read_text()


def test_cors_and_sandbox_contract():
    env_text = (ROOT / "apps/api/.env.example").read_text()
    cors_line = next(line for line in env_text.splitlines() if line.startswith("APP_CORS_ORIGINS="))
    assert "[" not in cors_line
    assert "]" not in cors_line
    assert '"' not in cors_line
    assert "," in cors_line

    page = (ROOT / "apps/web/src/pages/dev/components.astro").read_text()
    sandbox = (ROOT / "apps/web/src/components/ApiSandbox.astro").read_text()
    assert "ApiSandbox" in page
    assert "Testar API e banco" in sandbox
    assert "APP_CORS_ORIGINS" in sandbox
    assert "/api/health" in sandbox
    assert "/api/health/db" in sandbox


def test_health_contract_is_standardized():
    main = (ROOT / "apps/api/main.py").read_text()
    health = (ROOT / "apps/api/routes/health.py").read_text()
    assert 'include_router(health_router, prefix="/api")' in main
    assert '@router.get("/health")' in health
    assert '@router.get("/health/db")' in health
    assert '"service": settings.app_service' in health
    assert 'status_code=200 if result["ok"] else 503' in health
