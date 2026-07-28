from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LOCAL = ROOT / "deploy/local"
REMOTE = ROOT / "deploy/remote"


def text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def test_setup_contract_local():
    setup = text(LOCAL / "setup.sh")
    assert '"$D/setup-api.sh"' in setup
    assert '"$D/setup-web.sh"' in setup
    assert '"$D/start-api.sh"' in text(LOCAL / "setup-api.sh")
    assert '"$D/start-web.sh"' in text(LOCAL / "setup-web.sh")
    assert "fuser -k" in text(LOCAL / "setup-api.sh")
    assert "fuser -k" in text(LOCAL / "setup-web.sh")


def test_start_contract_local():
    start = text(LOCAL / "start.sh")
    assert '"$D/start-api.sh"' in start
    assert '"$D/start-web.sh"' in start
    assert "setup-api.sh" not in start
    assert "setup-web.sh" not in start


def test_setup_contract_remote():
    setup = text(REMOTE / "setup.sh")
    assert "rsync -az --delete" in setup
    assert '"$D/setup-api.sh"' in setup
    assert '"$D/setup-web.sh"' in setup
    assert '"$D/start-api.sh"' in text(REMOTE / "setup-api.sh")
    assert '"$D/start-web.sh"' in text(REMOTE / "setup-web.sh")
    assert "env_tools.py" in text(REMOTE / "setup-api.sh")
    assert "env_tools.py" in text(REMOTE / "setup-web.sh")


def test_remote_target_and_units_are_aligned():
    target = text(REMOTE / "target.conf")
    assert "DEPLOY_REMOTE_ROOT=/home/ubuntu/apps/orgs/orbital/orbital-mail" in target
    assert "DEPLOY_API_PORT=8106" in target
    assert "DEPLOY_WEB_PORT=4106" in target
    api = text(REMOTE / "systemd/orbital-mail-api.service")
    web = text(REMOTE / "systemd/orbital-mail-web.service")
    for unit in (api, web):
        assert "/home/ubuntu/apps/orgs/orbital/orbital-mail/" in unit
        assert "/home/ubuntu/apps/orbital/orbital-mail/" not in unit
    assert "--port 8106" in api
    assert "PORT=4106" in web


def test_no_parallel_remote_deploy_flow():
    assert not (REMOTE / "push.sh").exists()
    assert not (REMOTE / "install-services.sh").exists()


def test_test_orchestration_contract():
    for directory in (LOCAL, REMOTE):
        runner = text(directory / "test.sh")
        assert '"$D/test-api.sh"' in runner
        assert '"$D/test-web.sh"' in runner
        assert (directory / "test-api.sh").is_file()
        assert (directory / "test-web.sh").is_file()
