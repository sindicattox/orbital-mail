from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_queue_endpoints_are_dev_only():
    source = (ROOT / 'apps/api/mail/router.py').read_text()
    for route in [
        "@router.get('/dispatch-preview')",
        "@router.get('/recipient-filters')",
        "@router.get('/campaigns/{campaign_id}/recipients')",
        "@router.get('/campaigns/{campaign_id}/queue')",
        "@router.post('/campaigns/{campaign_id}/queue/prepare/start')",
        "@router.post('/campaigns/{campaign_id}/queue/prepare/batch')",
        "@router.delete('/campaigns/{campaign_id}/queue')",
    ]:
        section = source[source.index(route):]
        section = section[:section.index('\n\n@router.', 1)] if '\n\n@router.' in section[1:] else section
        assert 'auth.require_dev()' in section


def test_queue_pages_and_navigation_are_dev_only():
    layout = (ROOT / 'apps/web/src/layouts/AppLayout.astro').read_text()
    css = (ROOT / 'apps/web/src/styles/global.css').read_text()
    queue_page = (ROOT / 'apps/web/src/pages/fila-envios/index.astro').read_text()
    recipients_page = (ROOT / 'apps/web/src/pages/campanhas/[id]/destinatarios.astro').read_text()

    assert "label: 'Fila de envios'" in layout
    assert 'body:not([data-is-dev="true"]) a[href*="/fila-envios"]' in css
    assert 'body[data-is-dev="true"] a[href*="/fila-envios"]' in css
    assert 'devOnly>' in queue_page
    assert 'devOnly>' in recipients_page


def test_campaign_list_hides_technical_actions_and_columns_from_normal_users():
    component = (ROOT / 'apps/web/public/components/mail.js').read_text()
    styles = (ROOT / 'apps/web/public/components/mail/styles.js').read_text()

    assert 'this.isDev' in component
    assert 'Ver fila' in component and 'Preparar' in component
    assert "'<tr><th>Ações</th><th>Nome interno</th><th>Assunto</th><th>Remetente</th><th>Status</th><th>Atualização</th></tr>'" in component
    assert ": '<tr><th>Ações</th><th>Assunto</th><th>Status</th><th>Atualização</th></tr>'" in component
    assert '.dev-action' in styles


def test_campaign_technical_fields_are_dev_only_and_normalized_before_submit():
    for relative in ['apps/web/src/pages/campanhas/nova.astro', 'apps/web/src/pages/campanhas/[id].astro']:
        source = (ROOT / relative).read_text()
        assert 'dev-only dev-highlight dev-field-group' in source
        assert 'name="internal_name"' in source
        assert 'name="sender_name"' in source
        assert 'name="sender_email"' in source
        assert 'name="body_text"' in source
        assert "'internal_name'" in source and "'sender_email'" in source


def test_non_dev_campaign_writes_ignore_technical_values():
    source = (ROOT / 'apps/api/mail/router.py').read_text()
    schemas = (ROOT / 'apps/api/mail/schemas.py').read_text()

    assert "TECHNICAL_CAMPAIGN_FIELDS = ('internal_name', 'body_text', 'sender_name', 'sender_email', 'reply_to')" in source
    assert "values[field] = current.get(field)" in source
    assert "'internal_name': values['subject'].strip()" in source
    assert "'sender_email': sender_email" in source
    assert "Configuração ausente: EMAIL_FROM_ADDRESS." in source
    assert 'internal_name: str | None' in schemas
    assert 'sender_email: EmailStr | None = None' in schemas


def test_non_dev_create_uses_server_sender_defaults_and_ignores_technical_payload(monkeypatch):
    import sys
    from types import SimpleNamespace
    sys.path.insert(0, str(ROOT / 'apps/api'))
    from core.auth import AuthContext
    from mail import router
    from mail.schemas import CampaignCreate

    monkeypatch.setattr(router, 'get_settings', lambda: SimpleNamespace(
        mail_from_name='ASAClub',
        mail_from_address='noreply@asaclub.org.br',
        mail_reply_to='contato@asaclub.org.br',
    ))
    auth = AuthContext(91, 'asaclub', False, False, frozenset({('orbital-mail-home', 'access_page')}))
    payload = CampaignCreate(
        subject='Campanha de agosto',
        body_html='<p>Olá</p>',
        internal_name='tentativa técnica',
        body_text='não deve entrar',
        sender_name='Outro',
        sender_email='outro@example.org',
        reply_to='outro@example.org',
    )

    values = router._campaign_write_values(payload, auth)

    assert values['internal_name'] == 'Campanha de agosto'
    assert values['body_text'] is None
    assert values['sender_name'] == 'ASAClub'
    assert values['sender_email'] == 'noreply@asaclub.org.br'
    assert values['reply_to'] == 'contato@asaclub.org.br'


def test_non_dev_update_preserves_technical_campaign_fields():
    import sys
    sys.path.insert(0, str(ROOT / 'apps/api'))
    from core.auth import AuthContext
    from mail import router
    from mail.schemas import CampaignUpdate

    auth = AuthContext(91, 'asaclub', False, False, frozenset({('orbital-mail-home', 'access_page')}))
    current = {
        'internal_name': 'Interno original',
        'body_text': 'Texto original',
        'sender_name': 'ASAClub',
        'sender_email': 'noreply@asaclub.org.br',
        'reply_to': 'contato@asaclub.org.br',
    }
    payload = CampaignUpdate(
        subject='Assunto novo',
        body_html='<p>Novo</p>',
        internal_name='tentativa',
        body_text='tentativa',
        sender_name='Tentativa',
        sender_email='tentativa@example.org',
        reply_to='tentativa@example.org',
    )

    values = router._campaign_write_values(payload, auth, current)

    for field in router.TECHNICAL_CAMPAIGN_FIELDS:
        assert values[field] == current[field]
    assert values['subject'] == 'Assunto novo'
    assert values['body_html'] == '<p>Novo</p>'
