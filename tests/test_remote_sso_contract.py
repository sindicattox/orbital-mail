from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_remote_mail_sso_uses_admin_and_real_callback():
    target = (ROOT / 'deploy/remote/target.conf').read_text(encoding='utf-8')
    setup = (ROOT / 'deploy/remote/setup-api.sh').read_text(encoding='utf-8')
    assert 'DEPLOY_ORBITAL_URL=https://admin.anpprev.org' in target
    assert 'AUTH_AUTHORIZE_URL=$DEPLOY_ORBITAL_URL/auth/sso/authorize' in setup
    assert 'AUTH_REDIRECT_URI=$DEPLOY_PUBLIC_URL/api/mail/auth/callback' in setup
