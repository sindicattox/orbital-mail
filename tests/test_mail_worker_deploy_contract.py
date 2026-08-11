from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_worker_is_module_owned_and_separate_from_api_process():
    local = (ROOT / "deploy/local/workers.sh").read_text()
    start_api = (ROOT / "deploy/local/start-api.sh").read_text()
    worker = (ROOT / "apps/api/workers/mail_send_worker.py").read_text()

    assert "-m workers.mail_send_worker" in local
    assert 'readlink -f "$proc_dir/cwd"' in local
    assert '[[ "$cwd" == "$API_DIR" ]]' in local
    assert "pkill" not in local and "killall" not in local
    assert "mail_send_worker" not in start_api
    assert "FOR UPDATE SKIP LOCKED" not in worker
    assert "MailDeliveryWorkerService" in worker


def test_worker_uses_small_isolated_oracle_pool_and_master_send_switch():
    worker = (ROOT / "apps/api/workers/mail_send_worker.py").read_text()
    for context in ("local", "production"):
        config = (ROOT / f"apps/api/config/{context}/app.env").read_text()
        assert "ORACLE_MAIL_WORKER_POOL_SIZE=1" in config
        assert "MAIL_WORKER_SYSTEMD_SERVICE=orbital-mail-send-worker.service" in config
    assert 'os.environ["ORACLE_POOL_MAX_OVERFLOW"] = "0"' in worker
    assert "settings.mail_send_enabled" in worker
    assert "EMAIL_SEND_ENABLED=false" in (ROOT / "apps/api/config/production/services.env").read_text()


def test_local_and_remote_setup_start_worker_once():
    local_setup = (ROOT / "deploy/local/setup.sh").read_text()
    remote_setup = (ROOT / "deploy/remote/setup.sh").read_text()

    assert local_setup.count('"$SCRIPT_DIR/workers.sh"') == 1
    assert remote_setup.count('"$SCRIPT_DIR/workers.sh"') == 1
    assert 'wait "$WORKERS_PID"' in remote_setup


def test_remote_worker_is_restartable_systemd_service():
    unit = (ROOT / "deploy/remote/systemd/orbital-mail-send-worker.service").read_text()
    workers = (ROOT / "deploy/remote/workers.sh").read_text()

    assert "ExecStart=__REMOTE_ROOT__/apps/api/.venv/bin/python -m workers.mail_send_worker" in unit
    assert "Restart=always" in unit
    assert "MAIL_WORKER_SYSTEMD_SERVICE" in workers
    assert 'sudo systemctl restart "$WORKER_SERVICE"' in workers
    assert "/api/health/worker" in workers
