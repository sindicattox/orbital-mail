from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LOCAL = ROOT / 'deploy/local'
REMOTE = ROOT / 'deploy/remote'

def text(path):
    return path.read_text(encoding='utf-8')

def test_local_contract_matches_orbital_app():
    assert '"$SCRIPT_DIR/setup-api.sh"' in text(LOCAL / 'setup.sh')
    assert '"$SCRIPT_DIR/setup-web.sh"' in text(LOCAL / 'setup.sh')
    assert 'load_config_context "$API_DIR"' in text(LOCAL / 'start-api.sh')
    assert 'load_config_context "$WEB_DIR"' in text(LOCAL / 'start-web.sh')

def test_remote_contract_matches_orbital_app():
    setup = text(REMOTE / 'setup.sh')
    assert 'rsync -az --delete' in setup
    assert "--exclude='*.remove'" in setup
    assert '"$SCRIPT_DIR/setup-api.sh"' in setup
    assert '"$SCRIPT_DIR/setup-web.sh"' in setup
    target = text(REMOTE / 'target.conf')
    assert 'DEPLOY_REMOTE_ROOT=/home/ubuntu/apps/orgs/orbital/orbital-mail' in target
    assert 'DEPLOY_API_PORT' not in target
    assert 'DEPLOY_WEB_PORT' not in target

def test_config_tree_and_controlled_removals():
    for app in ('api', 'web'):
        for context in ('local', 'production'):
            assert (ROOT / f'apps/{app}/config/{context}/app.env').is_file()
            assert (ROOT / f'apps/{app}/config/{context}/services.env').is_file()
    assert (ROOT / 'apps/api/.env.example.remove').is_file()
    assert (ROOT / 'apps/web/.env.example.remove').is_file()
    assert (ROOT / 'deploy/core/env_tools.py.remove').is_file()
