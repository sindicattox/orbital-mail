from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_campaign_dynamic_routes_are_server_rendered():
    routes = [
        ROOT / "apps/web/src/pages/campanhas/[id].astro",
        ROOT / "apps/web/src/pages/campanhas/[id]/destinatarios.astro",
    ]

    for route in routes:
        source = route.read_text(encoding="utf-8")
        assert "export const prerender = false;" in source
