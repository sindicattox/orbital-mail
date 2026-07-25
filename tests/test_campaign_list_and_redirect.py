from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_campaign_select_normalizes_legacy_null_internal_name():
    source = (ROOT / 'apps/api/mail/router.py').read_text()
    assert "NVL(NULLIF(TRIM(internal_name), '')" in source
    assert "'Campanha ' || TO_CHAR(id)" in source
    assert "'Sem assunto'" in source
    assert "NVL(LOWER(status), 'draft') AS status" in source


def test_new_campaign_returns_to_list_after_save():
    source = (ROOT / 'apps/web/src/pages/campanhas/nova.astro').read_text()
    assert "window.location.href = '/campanhas?saved=1';" in source
    assert '`/campanhas/${result.id}?saved=1`' not in source


def test_campaign_list_shows_saved_feedback_and_cleans_url():
    source = (ROOT / 'apps/web/src/pages/campanhas/index.astro').read_text()
    assert "Campanha cadastrada com sucesso." in source
    assert "history.replaceState({}, '', '/campanhas');" in source
