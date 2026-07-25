from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EDITOR = ROOT / 'apps/web/src/components/orbital-html-editor'


def test_editor_is_isolated_in_own_files():
    assert (EDITOR / 'OrbitalHtmlEditor.astro').exists()
    assert (EDITOR / 'editor.js').exists()
    assert (EDITOR / 'editor.css').exists()


def test_editor_supports_paste_and_upload_without_base64():
    source = (EDITOR / 'editor.js').read_text(encoding='utf-8')
    assert "addEventListener('paste'" in source
    assert "FormData" in source
    assert "readAsDataURL" not in source
    assert "data:image" not in source


def test_campaign_pages_use_shared_editor():
    for page in ('nova.astro', '[id].astro'):
        source = (ROOT / 'apps/web/src/pages/campanhas' / page).read_text(encoding='utf-8')
        assert 'OrbitalHtmlEditor' in source
        assert 'name="body_html"' in source
