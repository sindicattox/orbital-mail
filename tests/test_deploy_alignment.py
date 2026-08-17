import os
from pathlib import Path

MAIL_ROOT = Path(__file__).resolve().parents[1]
APP_ROOT = Path(os.environ.get("ORBITAL_APP_ROOT", MAIL_ROOT.parent / "orbital-app")).resolve()


def read(root: Path, rel: str) -> str:
    return (root / rel).read_text(encoding="utf-8")


def test_reference_exists():
    assert APP_ROOT.is_dir(), f"orbital-app não encontrado em {APP_ROOT}"


def test_contract_and_wallet_upload_are_app_only():
    assert (APP_ROOT / "deploy/CONTRACT.md").is_file()
    assert not (MAIL_ROOT / "deploy/CONTRACT.md").exists()
    assert not (MAIL_ROOT / "deploy/CONTRACT.md.remover").exists()
    assert (APP_ROOT / "deploy/remote/wallet-upload.sh").is_file()
    assert not (MAIL_ROOT / "deploy/remote/wallet-upload.sh").exists()
    assert not (MAIL_ROOT / "deploy/remote/wallet-upload.sh.remover").exists()
    assert (MAIL_ROOT / "deploy/local/workers.sh").is_file()
    assert (MAIL_ROOT / "deploy/remote/workers.sh").is_file()


def test_generic_scripts_follow_orbital_app():
    assert read(MAIL_ROOT, "deploy/local/setup-api.sh") == read(APP_ROOT, "deploy/local/setup-api.sh")
    mail_setup_web = read(MAIL_ROOT, "deploy/local/setup-web.sh")
    assert 'APP_CONFIG="$WEB_DIR/config/local/app.env"' in mail_setup_web
    assert "WEB_PORT=\"$(sed -n 's/^APP_PORT=//p' \"$APP_CONFIG\")\"" in mail_setup_web
    assert "WEB_PORT=4106" not in mail_setup_web
    assert read(MAIL_ROOT, "deploy/local/start.sh") == read(APP_ROOT, "deploy/local/start.sh")
    assert read(MAIL_ROOT, "deploy/remote/setup-api.sh") == read(APP_ROOT, "deploy/remote/setup-api.sh")
    assert read(MAIL_ROOT, "deploy/remote/setup-web.sh") == read(APP_ROOT, "deploy/remote/setup-web.sh")
    assert read(MAIL_ROOT, "deploy/remote/start-api.sh") == read(APP_ROOT, "deploy/remote/start-api.sh")
    assert read(MAIL_ROOT, "deploy/remote/start.sh") == read(APP_ROOT, "deploy/remote/start.sh")
    assert read(MAIL_ROOT, "deploy/remote/systemd/install.sh") == read(APP_ROOT, "deploy/remote/systemd/install.sh")


def test_remote_setup_has_no_app_only_steps():
    source = read(MAIL_ROOT, "deploy/remote/setup.sh")
    assert '"$SCRIPT_DIR/setup-api.sh"' in source
    assert '"$SCRIPT_DIR/setup-web.sh"' in source
    assert "wallet-upload.sh" not in source
    assert source.count('"$SCRIPT_DIR/workers.sh"') == 1
    assert "--exclude='*.remover'" in source
    assert "--exclude='*.external'" in source


def test_target_conf_contains_only_mail_destination():
    target = read(MAIL_ROOT, "deploy/remote/target.conf")
    assert "DEPLOY_REMOTE_ROOT=/home/ubuntu/apps/orgs/orbital/orbital-mail" in target
    assert "DEPLOY_LOCAL_WALLET_DIR" not in target
    assert "DEPLOY_REMOTE_WALLET_DIR" not in target


def test_applications_select_config_with_same_base_loader():
    assert read(MAIL_ROOT, "apps/api/core/load_env.py") == read(APP_ROOT, "apps/api/core/load_env.py")
    assert read(MAIL_ROOT, "apps/web/scripts/load-env.mjs") == read(APP_ROOT, "apps/web/scripts/load-env.mjs")


def test_git_crypt_contract_matches_app():
    assert read(MAIL_ROOT, ".gitattributes") == read(APP_ROOT, ".gitattributes")
