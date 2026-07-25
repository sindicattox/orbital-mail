from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
GLOBAL_CSS = ROOT / "apps/web/src/styles/global.css"
APP_LAYOUT = ROOT / "apps/web/src/layouts/AppLayout.astro"


def test_global_css_has_no_late_imports():
    css = GLOBAL_CSS.read_text(encoding="utf-8")
    assert "@import" not in css


def test_ui_css_is_imported_by_main_layout_after_global_css():
    layout = APP_LAYOUT.read_text(encoding="utf-8")
    global_pos = layout.index("import '../styles/global.css';")
    ui_pos = layout.index("import '../styles/ui.css';")
    assert global_pos < ui_pos
