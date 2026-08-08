from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def read(path: str) -> str:
    return (ROOT / path).read_text(encoding='utf-8').lower()


def test_queue_uses_exact_existing_columns_without_person_id():
    source = read('apps/api/mail/queue.py')
    for column in ('email_campaign_id', 'member_id', 'member_insert_date', 'email', 'status', 'tenant_code', 'try_count'):
        assert column in source
    assert 'person_id' not in source


def test_queue_is_batched_and_idempotent():
    source = read('apps/api/mail/queue.py')
    assert 'rownum <= :batch_size' in source
    assert 'not exists' in source
    assert 'partition by lower(trim(e.email))' in source
    assert "'pending'" in source


def test_queue_uses_real_lookup_tables_and_member_columns():
    source = read('apps/api/mail/queue.py')
    router = read('apps/api/mail/router.py')
    assert 'br_situacao_associativa_code' in source
    assert 'br_situacao_funcional_code' in source
    assert 'from br_situacao_associativa' in router
    assert 'from br_situacao_funcional' in router
    assert "'desfiliado'" not in source


def test_queue_filters_tenant_blacklist_and_cutoff():
    source = read('apps/api/mail/queue.py')
    assert 'email_blacklist' in source
    assert 'lower(m.tenant_code) = lower(:tenant_code)' in source
    assert 'm.updated_at' in source
    assert ':cutoff' in source


def test_list_has_live_progress_and_queue_controls():
    component = read('apps/web/public/components/mail.js')
    assert 'preparar destinatários' in component
    assert 'queueprogress' in component
    assert '${current} de ${total}' in component
    assert 'batch_size: 250' in component
    assert 'limpar fila' in component


def test_recipients_page_uses_shared_table_and_input_styles():
    page = read('apps/web/src/pages/campanhas/[id]/destinatarios.astro')
    css = read('apps/web/src/styles/ui.css')
    assert 'data-table' in page
    assert 'situação associativa' in page
    assert 'situação funcional' in page
    assert '.list-filters' in css
    assert 'input,select,textarea' in css


def test_create_and_update_return_to_list():
    create_page = read('apps/web/src/pages/campanhas/nova.astro')
    edit_page = read('apps/web/src/pages/campanhas/[id].astro')
    assert "window.location.href = `${modulebase}/campanhas?saved=1`" in create_page
    assert "window.location.href=`${modulebase}/campanhas?saved=updated`" in edit_page
