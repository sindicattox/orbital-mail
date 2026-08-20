from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WEB = ROOT / "apps/web"


def test_layout_uses_orbital_ui_foundation_and_shared_navigation():
    layout = (WEB / "src/layouts/AppLayout.astro").read_text(encoding="utf-8")
    assert "@orbital/ui/tokens.css" in layout
    assert "@orbital/ui/base.css" in layout
    assert "OrbitalTopBar" in layout
    assert "OrbitalSidebar" in layout


def test_navigation_does_not_define_initial_badges():
    sources = []
    for relative in ("src/layouts/AppLayout.astro", "src/config/navigation.json", "src/config/navigation.mjs"):
        path = WEB / relative
        if path.exists():
            sources.append(path.read_text(encoding="utf-8"))
    combined = "\n".join(sources)
    assert "badge:" not in combined
    assert '"badge"' not in combined


def test_consumer_never_imports_private_orbital_ui_sources():
    for path in (WEB / "src").rglob("*"):
        if path.is_file() and path.suffix in {".astro", ".js", ".mjs", ".ts", ".css"}:
            source = path.read_text(encoding="utf-8")
            assert "node_modules/@orbital/ui/src" not in source, path
            assert "@orbital/ui/src" not in source, path
