from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EDITOR = ROOT / 'apps/web/src/components/orbital-html-editor'
EDITOR_SCRIPT = ROOT / 'apps/web/public/components/orbital-html-editor/editor.js'


def test_editor_is_isolated_in_own_files():
    assert (EDITOR / 'OrbitalHtmlEditor.astro').exists()
    assert EDITOR_SCRIPT.exists()
    assert (EDITOR / 'editor.js').exists()
    assert (EDITOR / 'editor.css').exists()
    bridge = (EDITOR / 'editor.js').read_text(encoding='utf-8')
    assert bridge.strip() == "export const EDITOR_SCRIPT_PATH = 'components/orbital-html-editor/editor.js';"


def test_editor_supports_paste_and_upload_without_base64():
    source = EDITOR_SCRIPT.read_text(encoding='utf-8')
    assert "addEventListener('paste'" in source
    assert "FormData" in source
    assert "readAsDataURL" not in source
    assert "data:image" not in source


def test_campaign_pages_use_shared_editor():
    for page in ('nova.astro', '[id].astro'):
        source = (ROOT / 'apps/web/src/pages/campanhas' / page).read_text(encoding='utf-8')
        assert 'OrbitalHtmlEditor' in source
        assert 'name="body_html"' in source


def test_editor_does_not_expose_deprecated_document_commands_to_diagnostics():
    source = EDITOR_SCRIPT.read_text(encoding='utf-8')
    assert 'document.execCommand' not in source
    assert 'document.queryCommandState' not in source
    assert 'document.queryCommandValue' not in source
    assert "callDocumentEditingApi('execCommand'" in source


def test_astro_define_vars_scripts_are_explicitly_inline():
    astro_root = ROOT / 'apps/web/src'
    for path in astro_root.rglob('*.astro'):
        source = path.read_text(encoding='utf-8')
        assert '<script define:vars=' not in source, path
        if 'define:vars=' in source:
            assert '<script is:inline define:vars=' in source, path


def test_editor_runtime_is_loaded_from_public_without_vite_entry():
    component = (EDITOR / 'OrbitalHtmlEditor.astro').read_text(encoding='utf-8')
    assert "const editorRuntimeTag = '<script src=\"/orbital-mail/components/orbital-html-editor/editor.js\"></script>';" in component
    assert '<Fragment set:html={editorRuntimeTag} />' in component
    assert '<script is:inline' not in component
    assert 'src={editorScriptUrl}' not in component
    assert "import { EDITOR_SCRIPT_PATH } from './editor.js';" not in component
    assert "import './editor.js'" not in component
