import os
from pathlib import Path

MAIL_ROOT = Path(__file__).resolve().parents[1]
APP_ROOT = Path(os.environ.get("ORBITAL_APP_ROOT", MAIL_ROOT.parent / "orbital-app")).resolve()

EXACT_COMMON = (
    "deploy/CONTRACT.md",
    "deploy/local/setup.sh",
    "deploy/local/start.sh",
    "deploy/local/start-web.sh",
    "deploy/remote/setup.sh",
    "deploy/remote/start.sh",
    "deploy/remote/wallet-upload.sh",
)

MAIL_ONLY = {
    "deploy/local/test-web.sh",
    "deploy/remote/test-public-image.sh",
    "deploy/remote/test-web.sh",
}

APP_ONLY = {
    "deploy/local/test-db-schema.sh",
    "deploy/local/test-db.sh",
    "deploy/local/test-login-real.sh",
    "deploy/local/test-oracle-pool-live.sh",
    "deploy/remote/test-db-schema.sh",
    "deploy/remote/test-db.sh",
    "deploy/remote/test-login-real.sh",
    "deploy/remote/test-oracle-pool-live.sh",
    "deploy/temp/inspect-oracle-pool.sh",
}


def read(root: Path, rel: str) -> str:
    return (root / rel).read_text(encoding="utf-8")


def deploy_files(root: Path) -> set[str]:
    return {
        str(path.relative_to(root))
        for path in (root / "deploy").rglob("*")
        if path.is_file()
        and "__pycache__" not in path.parts
        and path.suffix != ".pyc"
    }


def test_reference_exists():
    assert APP_ROOT.is_dir(), f"orbital-app não encontrado em {APP_ROOT}"


def test_generic_deploy_files_are_byte_for_byte_equal():
    for rel in EXACT_COMMON:
        assert read(MAIL_ROOT, rel) == read(APP_ROOT, rel), rel


def test_deploy_tree_diff_is_explicit():
    app = deploy_files(APP_ROOT)
    mail = deploy_files(MAIL_ROOT)
    assert mail - app == MAIL_ONLY
    assert app - mail == APP_ONLY


def test_target_conf_has_same_generic_keys_and_mail_root_only():
    def keys(root: Path):
        return [
            line.split("=", 1)[0]
            for line in read(root, "deploy/remote/target.conf").splitlines()
            if line and not line.startswith("#")
        ]

    assert keys(MAIL_ROOT) == keys(APP_ROOT)
    mail = read(MAIL_ROOT, "deploy/remote/target.conf")
    assert "DEPLOY_REMOTE_ROOT=/home/ubuntu/apps/orgs/orbital/orbital-mail" in mail
    assert "DEPLOY_LOCAL_WALLET_DIR=/home/daniel/.oracle/Wallet_sindicatto" in mail
    assert "DEPLOY_REMOTE_WALLET_DIR=/home/ubuntu/.oracle/Wallet_sindicatto" in mail


def test_common_setup_scripts_only_diverge_for_module_identity():
    app_setup_api = read(APP_ROOT, "deploy/local/setup-api.sh")
    mail_setup_api = read(MAIL_ROOT, "deploy/local/setup-api.sh")
    assert mail_setup_api == app_setup_api.replace("API_PORT=8001", "API_PORT=8106")

    app_setup_web = read(APP_ROOT, "deploy/local/setup-web.sh")
    mail_setup_web = read(MAIL_ROOT, "deploy/local/setup-web.sh")
    assert mail_setup_web == app_setup_web.replace("WEB_PORT=4001", "WEB_PORT=4106")

    app_remote_web = read(APP_ROOT, "deploy/remote/setup-web.sh")
    expected_remote_web = app_remote_web.replace("WEB_PORT=4001", "WEB_PORT=4106").replace(
        'WEB_SERVICE="orbital-app-web.service"',
        'WEB_SERVICE="orbital-mail-web.service"',
    )
    assert read(MAIL_ROOT, "deploy/remote/setup-web.sh") == expected_remote_web


def test_applications_select_config_with_same_base_loader():
    assert read(MAIL_ROOT, "apps/api/core/load_env.py") == read(APP_ROOT, "apps/api/core/load_env.py")
    assert read(MAIL_ROOT, "apps/web/scripts/load-env.mjs") == read(APP_ROOT, "apps/web/scripts/load-env.mjs")


def test_private_test_addresses_are_excluded_from_remote_sync():
    for root in (APP_ROOT, MAIL_ROOT):
        source = read(root, "deploy/remote/setup.sh")
        assert "--exclude='apps/api/.emails_para_teste'" in source
