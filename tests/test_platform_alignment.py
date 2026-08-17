from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_mail_uses_shared_guard_and_only_advertises_existing_routes():
    layout = (ROOT / "apps/web/src/layouts/AppLayout.astro").read_text(encoding="utf-8")
    main = (ROOT / "apps/api/main.py").read_text(encoding="utf-8")

    assert "from '@orbital/ui/auth-guard.js?raw'" in layout
    assert "data-orbital-protected" in layout
    assert 'data-auth-path="/auth/context"' in layout
    assert "/listas" not in layout
    assert "/modelos" not in layout
    assert 'docs_url="/docs" if _public_docs else None' in main


def test_mail_public_unsubscribe_stays_outside_the_protected_shell():
    page = (ROOT / "apps/web/src/pages/unsubscribe.astro").read_text(encoding="utf-8")
    assert "AppLayout" not in page
    assert "data-orbital-protected" not in page
