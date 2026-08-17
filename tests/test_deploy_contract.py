from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LOCAL = ROOT / "deploy/local"
REMOTE = ROOT / "deploy/remote"
SYSTEMD = REMOTE / "systemd"


def text(path):
    return path.read_text(encoding="utf-8")


def test_local_contract():
    setup = text(LOCAL / "setup.sh")
    assert '"$SCRIPT_DIR/setup-api.sh"' in setup
    assert '"$SCRIPT_DIR/setup-web.sh"' in setup
    assert '"$SCRIPT_DIR/workers.sh"' in setup
    assert '"http://127.0.0.1:${API_PORT}/api/health"' in text(LOCAL / "start-api.sh")
    assert "WEB_PORT=\"$(sed -n 's/^APP_PORT=//p' \"$APP_CONFIG\")\"" in text(LOCAL / "start-web.sh")
    assert 'http://127.0.0.1:${WEB_PORT}/orbital-mail/' in text(LOCAL / "start-web.sh")


def test_remote_contract():
    setup = text(REMOTE / "setup.sh")
    assert "rsync -az --delete" in setup
    assert "--exclude='*.remover'" in setup
    assert "--exclude='*.external'" in setup
    assert '"$SCRIPT_DIR/setup-api.sh"' in setup
    assert '"$SCRIPT_DIR/setup-web.sh"' in setup
    assert "wallet-upload.sh" not in setup
    assert '"$SCRIPT_DIR/workers.sh"' in setup
    assert (SYSTEMD / "install.sh").is_file()
    assert (SYSTEMD / "orbital-mail-api.service").is_file()
    assert (SYSTEMD / "orbital-mail-web.service").is_file()
    assert (SYSTEMD / "orbital-mail-send-worker.service").is_file()


def test_config_tree_and_controlled_removals():
    for app in ("api", "web"):
        for context in ("local", "production"):
            assert (ROOT / f"apps/{app}/config/{context}/app.env").is_file()
            assert (ROOT / f"apps/{app}/config/{context}/services.env").is_file()
    assert not (ROOT / "deploy/core").exists()
    assert not (ROOT / "apps/api/config/runtime").exists()
    assert not (ROOT / "apps/web/config/runtime").exists()
    assert not list(ROOT.rglob("*.remove"))
    assert not (ROOT / "deploy/CONTRACT.md").exists()
    assert not (ROOT / "deploy/CONTRACT.md.remover").exists()
    assert not (ROOT / "deploy/remote/wallet-upload.sh").exists()
    assert not (ROOT / "deploy/remote/wallet-upload.sh.remover").exists()
