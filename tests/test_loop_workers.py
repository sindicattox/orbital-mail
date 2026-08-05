from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
API = ROOT / 'apps' / 'api'
sys.path.insert(0, str(API))

from mail.test_loop_service import _dedupe_emails


def test_dedupe_emails_preserves_first_order():
    assert _dedupe_emails(['A@example.com', 'a@example.com', 'b@example.com']) == ['a@example.com', 'b@example.com']


def test_loop_page_and_api_contract():
    page = (ROOT / 'apps/web/src/pages/teste-loop/index.astro').read_text()
    service = (API / 'mail/test_loop_service.py').read_text()
    assert '/test-loop/start' in service
    assert 'FOR UPDATE SKIP LOCKED' in service
    assert 'ThreadPoolExecutor' in service
    assert 'EMAIL_QUEUE'.lower() in service.lower()
    assert '30 e-mails e 3 repetições' in page
    assert '90 envios' in page
    assert '/destinatarios' in page


def test_loop_limits_are_environment_settings():
    settings = (API / 'core/settings.py').read_text()
    example = ''.join(p.read_text() for p in sorted((ROOT / 'apps/api/config/local').glob('*.env')))
    for name in ('mail_test_max_workers', 'mail_test_max_recipients', 'mail_test_max_repetitions', 'mail_test_max_messages'):
        assert name in settings
    for name in ('EMAIL_TEST_MAX_WORKERS', 'EMAIL_TEST_MAX_RECIPIENTS', 'EMAIL_TEST_MAX_REPETITIONS', 'EMAIL_TEST_MAX_MESSAGES'):
        assert name in example


def test_test_email_allowlist_is_a_separate_private_file():
    service = (API / 'mail/test_loop_service.py').read_text()
    page = (ROOT / 'apps/web/src/pages/teste-loop/index.astro').read_text()
    gitignore = (ROOT / '.gitignore').read_text()
    assert 'TEST_EMAILS_FILE = API_DIR / ".emails_para_teste"' in service
    assert '/test-loop/allowed-emails' in service
    assert 'Destinatário(s) não autorizado(s)' in service
    assert 'apps/api/.emails_para_teste' in page
    assert 'readonly' in page
    assert 'MAIL_TEST_RECIPIENT_ALLOWLIST' not in ''.join(p.read_text() for p in sorted((ROOT / 'apps/api/config/local').glob('*.env')))
    assert 'apps/api/.emails_para_teste' in gitignore
    assert (API / '.emails_para_teste.example').is_file()


def test_reservation_applies_execution_options_before_execute():
    service = (API / 'mail/test_loop_service.py').read_text()
    assert 'statement = text(' in service
    assert ').execution_options(stream_results=True, yield_per=1)' in service
    assert ').execution_options(stream_results=True, yield_per=1).mappings()' not in service


def test_loop_manager_failure_is_visible_and_not_stuck():
    service = (API / 'mail/test_loop_service.py').read_text()
    assert "SET status = 'error'" in service
    assert 'Worker interrompido ou API recarregada' in service
    assert 'manager_active' in service


def test_test_campaign_respects_real_oracle_unique_constraint():
    service = (API / 'mail/test_loop_service.py').read_text()
    assert 'UK_EMAIL_CAMPAIGN_STATS' in service
    assert 'send_date, status' in service
    assert "SYSDATE, 'sending'" in service
    assert 'campaign_subject = f"[TESTE {marker}] {payload.subject}"[:500]' in service
    assert 'uuid4().hex[:8]' in service


def test_campaign_and_queue_are_atomic_and_errors_are_controlled():
    service = (API / 'mail/test_loop_service.py').read_text()
    assert 'except IntegrityError as exc:' in service
    assert service.count('db.rollback()') >= 4
    assert 'Não foi possível gerar uma identificação única' in service
    assert 'Não foi possível criar a campanha e a fila de teste no Oracle.' in service
    # O gerenciador só é registrado depois que campanha e fila foram confirmadas.
    assert service.index('campaign_id = _create_test_campaign_and_queue') < service.index('_stop_events[campaign_id] = stop_event')


def test_private_email_file_is_never_shipped_in_zip_source_tree():
    assert not (API / '.emails_para_teste').exists()
    assert (API / '.emails_para_teste.example').exists()
