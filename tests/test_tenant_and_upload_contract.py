from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_tenant_is_not_fixed_in_environment():
    settings = (ROOT / 'apps/api/core/settings.py').read_text()
    env_example = ''.join(p.read_text() for p in sorted((ROOT / 'apps/api/config/local').glob('*.env')))
    router = (ROOT / 'apps/api/mail/router.py').read_text()

    assert 'mail_tenant_code' not in settings.lower()
    assert 'MAIL_TENANT_CODE' not in env_example
    assert 'auth.tenant_code' in router


def test_upload_is_public_and_separated_by_authenticated_tenant():
    images = (ROOT / 'apps/api/mail/images.py').read_text()
    storage = (ROOT / 'apps/api/mail/image_storage.py').read_text()
    env_example = ''.join(p.read_text() for p in sorted((ROOT / 'apps/api/config/local').glob('*.env')))

    assert 'auth.tenant_code' in images
    assert 'mail_public_upload_url' in images
    assert '@router.get("/uploads/{tenant_code}/{filename}"' in images
    assert 'tenant_upload_dir(settings, tenant_code)' in images
    assert 'configured.replace("{tenant}", tenant)' in storage
    assert 'EMAIL_UPLOAD_PUBLIC_URL=https://admin.localhost/orbital-mail/api/mail/uploads' in env_example


def test_editor_upload_credentials_timeout_and_active_buttons():
    editor = (ROOT / 'apps/web/public/components/orbital-html-editor/editor.js').read_text()
    css = (ROOT / 'apps/web/src/components/orbital-html-editor/editor.css').read_text()

    assert "credentials: 'include'" in editor
    assert '30_000' in editor
    assert 'updateToolbarState' in editor
    assert "aria-pressed" in editor
    assert 'box-shadow:inset' in css


def test_auth_is_always_remote_and_has_no_dev_bypass():
    settings = (ROOT / 'apps/api/core/settings.py').read_text()
    auth = (ROOT / 'apps/api/core/auth.py').read_text()
    env_example = ''.join(p.read_text() for p in sorted((ROOT / 'apps/api/config/local').glob('*.env')))

    assert 'AUTH_MODE=remote' in env_example
    assert 'AUTH_DEV_' not in env_example
    assert '_standalone_context' not in auth
    assert 'auth_mode == "standalone"' not in auth
    assert 'AUTH_MODE deve ser remote no orbital-mail.' in settings


def test_production_rejects_non_public_image_url():
    settings = (ROOT / 'apps/api/core/settings.py').read_text()

    assert 'EMAIL_UPLOAD_PUBLIC_URL com HTTPS público' in settings
    assert 'EMAIL_UPLOAD_PUBLIC_URL sem endereço local' in settings
