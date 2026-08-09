from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def read(rel: str) -> str:
    return (ROOT / rel).read_text(encoding="utf-8")


def test_web_public_paths_are_identical_local_and_production():
    for context in ("local", "production"):
        app = read(f"apps/web/config/{context}/app.env")
        services = read(f"apps/web/config/{context}/services.env")
        assert "PUBLIC_API_URL=/orbital-mail/api/mail" in app
        assert services == "PUBLIC_ORBITAL_HOME_URL=/\n"


def test_api_auth_contract_is_identical_and_mandatory():
    local = read("apps/api/config/local/auth.env")
    production = read("apps/api/config/production/auth.env")
    assert local == production
    assert local == (
        "AUTH_CONTEXT_URL=http://127.0.0.1:8001/auth/context\n"
        "AUTH_MODE=remote\n"
        "AUTH_TIMEOUT_SECONDS=5\n"
    )


def test_no_browser_direct_port_urls_remain():
    web = "\n".join(path.read_text(encoding="utf-8") for path in (ROOT / "apps/web").rglob("*") if path.is_file())
    for forbidden in ("127.0.0.1:8106", "localhost:8106", "127.0.0.1:4106", "localhost:4106"):
        assert forbidden not in web


def test_astro_and_navigation_use_module_base():
    assert "base: '/orbital-mail'" in read("apps/web/astro.config.mjs")
    layout = read("apps/web/src/layouts/AppLayout.astro")
    assert "import.meta.env.BASE_URL" in layout
    assert 'src={`${moduleBase}/scripts/api-errors.js`}' in layout
    campaign = read("apps/web/src/pages/campanhas/index.astro")
    assert 'src={`${moduleBase}/components/mail.js`}' in campaign


def test_local_api_start_has_no_uvicorn_8000_fallback():
    source = read("deploy/local/start-api.sh")
    assert '--port "$API_PORT"' in source
    assert '--host "$API_HOST"' in source
    assert 'main:app --reload\n' not in source


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
    assert "http://127.0.0.1:4106/orbital-mail/" in source
    assert "http://127.0.0.1:4106/ >/dev/null" not in source


def _env_map(rel: str) -> dict[str, str]:
    result = {}
    for line in read(rel).splitlines():
        if line:
            key, value = line.split("=", 1)
            result[key] = value
    return result


def test_runtime_behavior_config_is_identical_local_and_production():
    assert read("apps/api/config/local/app.env") == read("apps/api/config/production/app.env")
    assert read("apps/api/config/local/auth.env") == read("apps/api/config/production/auth.env")
    assert read("apps/web/config/local/app.env") == read("apps/web/config/production/app.env")
    assert read("apps/web/config/local/services.env") == read("apps/web/config/production/services.env")

    local_db = _env_map("apps/api/config/local/database.env")
    production_db = _env_map("apps/api/config/production/database.env")
    assert {k for k in local_db if local_db[k] != production_db[k]} == {"ORACLE_WALLET_DIR"}

    local_services = _env_map("apps/api/config/local/services.env")
    production_services = _env_map("apps/api/config/production/services.env")
    assert {k for k in local_services if local_services[k] != production_services[k]} == {
        "EMAIL_UPLOAD_DIR", "EMAIL_UPLOAD_PUBLIC_URL", "MAIL_PUBLIC_URL"
    }


def test_application_never_detects_local_or_remote_from_filesystem_path():
    api_loader = read("apps/api/core/load_env.py")
    web_loader = read("apps/web/scripts/load-env.mjs")
    assert 'CONFIG_CONTEXT = "runtime"' in api_loader
    assert "path.join(webRoot, 'config', 'runtime')" in web_loader
    assert "/home/daniel/" not in api_loader
    assert "/home/daniel/" not in web_loader
    assert "includes('/home/" not in web_loader


def test_local_runs_with_production_runtime_mode_and_loopback_bind():
    local_api = _env_map("apps/api/config/local/app.env")
    production_api = _env_map("apps/api/config/production/app.env")
    local_web = _env_map("apps/web/config/local/app.env")
    production_web = _env_map("apps/web/config/production/app.env")
    assert local_api["APP_ENV"] == production_api["APP_ENV"] == "production"
    assert local_api["APP_HOST"] == production_api["APP_HOST"] == "127.0.0.1"
    assert local_web["APP_HOST"] == production_web["APP_HOST"] == "127.0.0.1"

