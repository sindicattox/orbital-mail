from pathlib import Path


def test_astro_server_build_uses_node_adapter():
    config = Path('apps/web/astro.config.mjs').read_text(encoding='utf-8')
    package = Path('apps/web/package.json').read_text(encoding='utf-8')

    assert "import node from '@astrojs/node'" in config
    assert "output: 'server'" in config
    assert "adapter: node({ mode: 'standalone' })" in config
    assert "defineConfig({" in config
    assert "defineConfig((" not in config
    assert '"@astrojs/node"' in package
