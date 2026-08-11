from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]

def test_remote_mail_auth_comes_from_production_config():
    target=(ROOT/'deploy/remote/target.conf').read_text()
    auth=(ROOT/'apps/api/config/production/auth.env').read_text()
    assert 'admin.anpprev.org' not in target
    assert 'AUTH_MODE=remote' in auth
    assert 'AUTH_CONTEXT_URL=http://127.0.0.1:8001/auth/context/module' in auth
