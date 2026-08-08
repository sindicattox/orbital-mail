from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]

def test_required_structure():
    required = [
        'apps/api/main.py','apps/api/core/auth.py','apps/api/core/settings.py','apps/api/mail/router.py',
        'apps/web/package.json','apps/web/src/pages/index.astro','apps/web/src/config/api-url.ts',
        'deploy/CONTRACT.md','deploy/local/setup.sh','deploy/local/start.sh',
        'deploy/local/test.sh','deploy/remote/setup.sh','deploy/remote/start.sh','deploy/remote/test.sh',
        'deploy/remote/target.conf',
    ]
    assert not [path for path in required if not (ROOT/path).exists()]

def test_ports_and_services_are_in_config_not_target():
    assert 'APP_PORT=4106' in (ROOT/'apps/web/config/local/app.env').read_text()
    assert 'APP_PORT=8106' in (ROOT/'apps/api/config/local/app.env').read_text()
    target=(ROOT/'deploy/remote/target.conf').read_text()
    assert 'APP_PORT' not in target and 'SYSTEMD_SERVICE' not in target
    assert 'API_SYSTEMD_SERVICE=orbital-mail-api.service' in (ROOT/'apps/api/config/production/app.env').read_text()
    assert 'WEB_SYSTEMD_SERVICE=orbital-mail-web.service' in (ROOT/'apps/web/config/production/app.env').read_text()

def test_config_files_are_canonical():
    for path in ROOT.glob('apps/*/config/*/*.env'):
        lines=path.read_text().splitlines()
        assert all(lines)
        assert all(not line.startswith('#') for line in lines)
        keys=[line.split('=',1)[0] for line in lines]
        assert keys == sorted(keys)
