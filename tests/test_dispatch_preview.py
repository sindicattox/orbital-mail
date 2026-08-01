from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_dispatch_preview_is_tenant_scoped_and_only_shows_disparable_items():
    queue_source = (ROOT / 'apps/api/mail/queue.py').read_text()
    router_source = (ROOT / 'apps/api/mail/router.py').read_text()

    assert "LOWER(q.tenant_code) = LOWER(:tenant_code)" in queue_source
    assert "LOWER(q.status) IN ('pending', 'processing')" in queue_source
    assert "def dispatch_preview(" in queue_source
    assert "@router.get('/dispatch-preview')" in router_source
    assert "settings.mail_send_enabled" in router_source


def test_dispatch_preview_page_is_visible_in_top_menu_and_never_changes_queue():
    layout = (ROOT / 'apps/web/src/layouts/AppLayout.astro').read_text()
    page = (ROOT / 'apps/web/src/pages/fila-envios/index.astro').read_text()

    assert "label: 'Fila de envios'" in layout
    assert "href: '/fila-envios'" in layout
    assert '/dispatch-preview' in page
    assert 'EMAIL_SEND_ENABLED=true' in page
    assert "method: 'POST'" not in page
    assert '/queue/prepare' not in page


def test_dispatch_preview_campaign_group_by_covers_oracle_expression_columns():
    queue_source = (ROOT / 'apps/api/mail/queue.py').read_text()

    assert 'GROUP BY q.email_campaign_id, c.id, c.internal_name, c.subject, c.status' in queue_source
