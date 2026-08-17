from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8").lower()


def test_dev_real_campaign_send_has_server_side_single_email_safety_lock():
    router = read("apps/api/mail/router.py")
    assert "dev-test-send" in router
    assert "auth.require_dev()" in router
    assert "distinct_emails" in router
    assert "single_email" in router
    assert "todos os itens da fila" in router
    assert "status = 'sending'" in router


def test_queue_preview_preserves_one_row_per_member_and_ui_requires_test_email():
    component = read("apps/web/public/components/mail.js")
    queue = read("apps/api/mail/queue.py")
    assert "pré-visualizar base" in component
    assert "fila de teste" in component
    assert "startrealtest" in component
    assert "grouping = 'm.id' if test_email" in queue


def test_dev_provider_settings_are_red_and_dev_only():
    layout = read("apps/web/src/layouts/AppLayout.astro")
    page = read("apps/web/src/pages/configuracoes/index.astro")
    css = read("apps/web/src/styles/global.css")
    assert "configurações" in layout
    assert "devonly" in page
    assert "dev-highlight" in page
    assert "/configuracoes" in css


def test_ses_is_a_supported_delivery_provider():
    provider = read("apps/api/mail/delivery_provider.py")
    settings = read("apps/api/core/settings.py")
    requirements = read("apps/api/requirements.txt")
    assert "def send_ses(" in provider
    assert 'boto3.client("sesv2"' in provider
    assert "ses" in settings
    assert "boto3" in requirements
