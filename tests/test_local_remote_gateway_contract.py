from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def read(rel: str) -> str:
    return (ROOT / rel).read_text(encoding="utf-8")


def _env_map(rel: str) -> dict[str, str]:
    result = {}
    for line in read(rel).splitlines():
        if line:
            key, value = line.split("=", 1)
            result[key] = value
    return result


def test_web_public_paths_are_identical_local_and_production():
    for context in ("local", "production"):
        app = read(f"apps/web/config/{context}/app.env")
        services = read(f"apps/web/config/{context}/services.env")
        assert "PUBLIC_API_URL=/orbital-mail/api/mail" in app
        assert services == "PUBLIC_ORBITAL_HOME_URL=/\n"


def test_api_auth_contract_is_identical_remote_and_mandatory():
    local = read("apps/api/config/local/auth.env")
    production = read("apps/api/config/production/auth.env")
    assert local == production
    assert local == (
        "AUTH_CONTEXT_URL=http://127.0.0.1:8001/auth/context/module\n"
        "AUTH_MODE=remote\n"
        "AUTH_TIMEOUT_SECONDS=5\n"
    )


def test_no_browser_direct_port_urls_remain_in_source():
    excluded = {"node_modules", ".astro", "dist", "__pycache__"}
    text_files = {
        ".astro", ".css", ".html", ".js", ".json", ".mjs", ".ts", ".tsx"
    }
    sources = []
    for path in (ROOT / "apps/web").rglob("*"):
        if not path.is_file() or any(part in excluded for part in path.parts):
            continue
        if path.suffix.lower() not in text_files:
            continue
        sources.append(path.read_text(encoding="utf-8"))
    web = "\n".join(sources)
    for forbidden in ("127.0.0.1:8106", "localhost:8106", "127.0.0.1:4106", "localhost:4106"):
        assert forbidden not in web


def test_astro_and_navigation_use_module_base():
    assert "base: '/orbital-mail'" in read("apps/web/astro.config.mjs")
    layout = read("apps/web/src/layouts/AppLayout.astro")
    assert "import.meta.env.BASE_URL" in layout
    assert "moduleBase}/scripts/api-errors.js" in layout
    campaign = read("apps/web/src/pages/campanhas/index.astro")
    assert "moduleBase}/components/mail.js" in campaign


def test_local_api_start_has_no_uvicorn_8000_fallback():
    source = read("deploy/local/start-api.sh")
    assert '--port "$API_PORT"' in source
    assert '--host "$API_HOST"' in source
    assert "config/runtime" not in source


def test_no_standalone_auth_bypass_remains():
    settings = read("apps/api/core/settings.py")
    auth = read("apps/api/core/auth.py")
    configs = read("apps/api/config/local/auth.env") + read("apps/api/config/production/auth.env")
    assert "standalone" not in configs
    assert "AUTH_DEV_" not in configs
    assert "_standalone_context" not in auth
    assert 'auth_mode == "standalone"' not in auth
    assert 'AUTH_MODE deve ser remote no orbital-mail.' in settings


def test_remote_web_health_check_uses_same_module_base():
    source = read("deploy/remote/start-web.sh")
    assert '"http://127.0.0.1:${WEB_PORT}/orbital-mail/"' in source
    assert '"http://127.0.0.1:${WEB_PORT}/"' not in source
    assert "config/runtime" not in source


def test_local_and_production_follow_orbital_app_environment_pattern():
    local_api = _env_map("apps/api/config/local/app.env")
    production_api = _env_map("apps/api/config/production/app.env")
    local_web = _env_map("apps/web/config/local/app.env")
    production_web = _env_map("apps/web/config/production/app.env")

    assert local_api["APP_ENV"] == "development"
    assert production_api["APP_ENV"] == "production"
    assert local_api["APP_HOST"] == local_web["APP_HOST"] == "0.0.0.0"
    assert production_api["APP_HOST"] == production_web["APP_HOST"] == "127.0.0.1"

    local_services = _env_map("apps/api/config/local/services.env")
    production_services = _env_map("apps/api/config/production/services.env")
    expected_differences = {
        "EMAIL_UPLOAD_DIR",
        "EMAIL_UPLOAD_PUBLIC_URL",
        "MAIL_PUBLIC_URL",
    }
    actual_differences = {key for key in local_services if local_services[key] != production_services[key]}
    assert expected_differences <= actual_differences <= expected_differences | {"MAIL_UNSUBSCRIBE_SECRET"}
    assert local_services["EMAIL_UPLOAD_PUBLIC_URL"].endswith("/orbital-mail/api/mail/uploads")
    assert production_services["EMAIL_UPLOAD_PUBLIC_URL"].endswith("/orbital-mail/api/mail/uploads")
    assert local_services["MAIL_PUBLIC_URL"].endswith("/orbital-mail")
    assert production_services["MAIL_PUBLIC_URL"].endswith("/orbital-mail")
    local_secret = local_services["MAIL_UNSUBSCRIBE_SECRET"]
    production_secret = production_services["MAIL_UNSUBSCRIBE_SECRET"]
    assert local_secret
    assert production_secret
    if local_secret != "********" or production_secret != "********":
        assert local_secret != production_secret
