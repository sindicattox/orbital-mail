from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
WEB = ROOT / "apps" / "web"


def test_mail_pages_have_h1_without_eyebrow_or_subtitle():
    pages = {
        "src/pages/index.astro": "Orbital Mail",
        "src/pages/campanhas/nova.astro": "Nova campanha",
        "src/pages/configuracoes/index.astro": "Configurações de envio",
        "src/pages/fila-envios/index.astro": "Fila atual de envios",
        "src/pages/modelos/index.astro": "Modelos de e-mail",
        "src/pages/teste-envio/index.astro": "Teste de envio",
    }
    for relative, title in pages.items():
        source = (WEB / relative).read_text(encoding="utf-8")
        assert f"<h1>{title}</h1>" in source, relative
        assert "class=\"eyebrow\"" not in source, relative
        assert "page-subtitle" not in source, relative


def test_mail_grid_matches_orbital_shell():
    css = (WEB / "src/styles/global.css").read_text()
    layout = (WEB / "src/layouts/AppLayout.astro").read_text()
    compact = css.replace(" ", "")
    assert "grid-template-columns:240pxminmax(0,1fr)" in compact
    assert "padding:1.25rem" in compact
    assert ".app-main{min-width:0;width:100%;padding:1.25rem;margin:0}" in compact
    assert "max-width:1600px" not in compact
    assert "import '@orbital/ui/tokens.css';" in layout
