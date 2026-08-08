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
