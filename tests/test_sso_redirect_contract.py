from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def text(rel: str) -> str:
    return (ROOT / rel).read_text(encoding="utf-8")


def test_local_and_production_use_same_gateway_sso_origin():
    expected = "PUBLIC_ORBITAL_HOME_URL=/\n"
    assert text("apps/web/config/local/services.env") == expected
    assert text("apps/web/config/production/services.env") == expected


def test_mail_sends_relative_return_to_for_same_origin_gateway():
    expected = "searchParams.set('return_to', `${window.location.pathname}${window.location.search}${window.location.hash}`)"
    for rel in (
        "apps/web/src/assets/auth/orbital-mail-auth.js",
        "apps/web/public/components/mail.js",
    ):
        source = text(rel)
        assert expected in source
        assert "window.location.href" not in source


def test_sso_redirect_is_module_agnostic():
    for rel in (
        "apps/web/src/assets/auth/orbital-mail-auth.js",
        "apps/web/public/components/mail.js",
    ):
        source = text(rel)
        assert "new URL('/login'" in source
        assert "4106" not in source
        assert "4001" not in source
        assert "admin.sindicatto.com" not in source
        assert "admin.localhost" not in source
