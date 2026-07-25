from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
API = ROOT / 'apps' / 'api'


def test_api_uses_only_existing_email_campaign_table():
    source = '\n'.join(
        path.read_text(encoding='utf-8')
        for path in API.rglob('*.py')
    ).upper()

    assert 'MAIL_CAMPAIGN_RECIPIENT' not in source
    assert 'FROM MAIL_CAMPAIGN' not in source
    assert 'JOIN MAIL_CAMPAIGN' not in source
    assert 'INTO MAIL_CAMPAIGN' not in source
    assert 'UPDATE MAIL_CAMPAIGN' not in source
    assert 'MAIL_CONTACT_LIST' not in source
    assert 'MAIL_CONTACT ' not in source
    assert 'EMAIL_CAMPAIGN' in source
