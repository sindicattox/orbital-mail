from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_test_send_page_reuses_editor_and_has_both_providers():
    page = (ROOT / "apps/web/src/pages/teste-envio/index.astro").read_text()
    assert "OrbitalHtmlEditor" in page
    assert 'value="smtp2go"' in page
    assert 'value="smtp"' in page
    assert "/test-send" in page


def test_home_and_navigation_link_to_test_send():
    home = (ROOT / "apps/web/src/pages/index.astro").read_text()
    layout = (ROOT / "apps/web/src/layouts/AppLayout.astro").read_text()
    assert 'href={`${moduleBase}/teste-envio`}' in home
    assert "href: `${moduleBase}/teste-envio`" in layout


def test_env_documents_both_providers_and_send_lock():
    env = ''.join(p.read_text() for p in sorted((ROOT / 'apps/api/config/local').glob('*.env')))
    for key in [
        "EMAIL_SEND_ENABLED=false",
        "SMTP2GO_API_KEY=",
        "SMTP_HOST=",
        "SMTP_PORT=465",
        "SMTP_SECURITY=tls",
    ]:
        assert key in env


def test_test_page_shows_provider_diagnostic():
    page = (ROOT / "apps/web/src/pages/teste-envio/index.astro").read_text()
    assert "Diagnóstico do provedor" in page
    assert "provider_message_id" in page
    assert "Aceito pelo provedor" in page
    assert "não significa entregue" in page
    assert "Copiar diagnóstico" in page
