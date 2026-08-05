from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WEB = ROOT / "apps/web"


def test_mail_uses_shared_orbital_top_bar():
    package = (WEB / "package.json").read_text()
    layout = (WEB / "src/layouts/AppLayout.astro").read_text()
    css = (WEB / "src/styles/global.css").read_text()

    assert '"@orbital/ui": "file:../../../orbital-ui"' in package
    assert "import { OrbitalTopBar } from '@orbital/ui';" in layout
    assert '<OrbitalTopBar' in layout
    assert 'moduleLabel="Mail"' in layout
    assert 'class="app-header"' not in layout
    assert '.app-header' not in css


def test_campaign_page_reuses_public_mail_component():
    page = (WEB / "src/pages/campanhas/index.astro").read_text()
    component = (WEB / "public/components/mail.js").read_text()

    assert '<orbital-mail api-base={apiUrl} standalone>' in page
    assert 'src="/components/mail.js"' in page
    assert "const TAG_NAME = 'orbital-mail';" in component
    assert "customElements.define(TAG_NAME, OrbitalMail)" in component
    assert "credentials: 'include'" in component
    assert "orbital-module-error" in component
    assert "orbitalSession" not in component


def test_remote_deploy_uses_standard_scripts_and_keeps_env_remote():
    remote = ROOT / "deploy/remote"
    setup = (remote / "setup.sh").read_text()
    target = (remote / "target.conf").read_text()

    assert (remote / 'push.sh.remove').exists()
    assert "--exclude='apps/api/.env'" in setup
    assert "--exclude='apps/web/.env'" in setup
    assert '"$SCRIPT_DIR/setup-api.sh"' in setup
    assert '"$SCRIPT_DIR/setup-web.sh"' in setup
    assert "DEPLOY_REMOTE_ROOT=/home/ubuntu/apps/orgs/orbital/orbital-mail" in target
    for name in ('setup-api.sh', 'setup-web.sh', 'setup.sh', 'start-api.sh', 'start-web.sh', 'start.sh', 'test.sh'):
        assert (ROOT / 'deploy/local' / name).exists()
        assert (remote / name).exists()
    for service_name in ('orbital-mail-api.service.remove', 'orbital-mail-web.service.remove'):
        assert (remote / 'systemd' / service_name).exists()
