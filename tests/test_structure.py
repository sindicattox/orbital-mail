from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_required_structure():
    required = [
        "apps/api/main.py",
        "apps/api/core/auth.py",
        "apps/api/core/settings.py",
        "apps/api/mail/router.py",
        "apps/api/mail/schemas.py",
        "apps/web/package.json",
        "apps/web/src/pages/index.astro",
        "apps/web/src/pages/campanhas/index.astro",
        "apps/web/src/pages/campanhas/nova.astro",
        "deploy/local/setup.sh",
        "deploy/local/start.sh",
        "deploy/remote/push.sh",
        "deploy/remote/systemd/orbital-mail-api.service",
        "deploy/remote/systemd/orbital-mail-web.service",
    ]
    missing = [path for path in required if not (ROOT / path).exists()]
    assert not missing, missing


def test_ports():
    assert "APP_PORT=4104" in (ROOT / "apps/web/.env.example").read_text()
    assert "APP_PORT=8104" in (ROOT / "apps/api/.env.example").read_text()


def test_real_mail_is_disabled_by_default():
    assert "EMAIL_PROVIDER=disabled" in (ROOT / "apps/api/.env.example").read_text()
