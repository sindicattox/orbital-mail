from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SYSTEMD = ROOT / "deploy" / "remote" / "systemd"


def test_remote_setup_owns_and_installs_mail_services():
    setup_api = (ROOT / "deploy/remote/setup-api.sh").read_text()
    setup_web = (ROOT / "deploy/remote/setup-web.sh").read_text()
    installer = (SYSTEMD / "install.sh").read_text()

    assert '"$API_SERVICE"' in setup_api
    assert '"$WEB_SERVICE"' in setup_web
    assert 'target_file="/etc/systemd/system/$service"' in installer
    assert 'sudo install -m 0644 "$rendered" "$target_file"' in installer
    assert "sudo systemctl daemon-reload" in installer
    assert 'sudo systemctl enable "$service"' in installer
    assert 'if ! cmp -s "$rendered" "$target_file"; then' in installer


def test_remote_services_belong_to_orbital_mail():
    api = (SYSTEMD / "orbital-mail-api.service").read_text()
    web = (SYSTEMD / "orbital-mail-web.service").read_text()

    assert "__REMOTE_ROOT__/apps/api/config/production/app.env" in api
    assert "__REMOTE_ROOT__/apps/web/config/production/app.env" in web
    assert "${APP_HOST}" in api and "${APP_PORT}" in api
    assert "--workers 2" in api
    assert "/usr/bin/node __REMOTE_ROOT__/apps/web/dist/server/entry.mjs" in web
    assert "orbital-mail-api.service" in web
    assert not list(SYSTEMD.glob("*worker*.service"))


def test_remote_scripts_use_configured_service_and_port():
    for rel in ("setup-api.sh", "start-api.sh"):
        source = (ROOT / "deploy/remote" / rel).read_text()
        assert "API_SYSTEMD_SERVICE" in source
        assert "APP_PORT" in source
        assert 'API_SERVICE="orbital-mail-api.service"' not in source
        assert "127.0.0.1:8106" not in source

    for rel in ("setup-web.sh", "start-web.sh"):
        source = (ROOT / "deploy/remote" / rel).read_text()
        assert "WEB_SYSTEMD_SERVICE" in source
        assert "APP_PORT" in source
        assert 'WEB_SERVICE="orbital-mail-web.service"' not in source
        assert "127.0.0.1:4106" not in source
