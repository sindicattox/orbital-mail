from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_mail_uses_reports_auth_contract_without_dedicated_sso():
    settings = (ROOT / "apps/api/core/settings.py").read_text(encoding="utf-8")
    auth = (ROOT / "apps/api/core/auth.py").read_text(encoding="utf-8")
    env = (ROOT / "apps/api/.env.example").read_text(encoding="utf-8")
    remote = (ROOT / "deploy/remote/setup-api.sh").read_text(encoding="utf-8")

    assert "AUTH_CONTEXT_URL" in env
    assert "AUTH_CLIENT_ID" not in env
    assert "AUTH_CLIENT_SECRET" not in env
    assert "AUTH_REDIRECT_URI" not in env
    assert "auth_context_url" in settings
    assert "AUTH_CONTEXT_URL=http://127.0.0.1:8001/auth/context" in remote
    assert "Authorization" in auth and "Bearer" in auth
    assert not (ROOT / "apps/api/core/auth_session.py").exists()
