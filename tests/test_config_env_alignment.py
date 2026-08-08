import os
from pathlib import Path

MAIL_ROOT = Path(__file__).resolve().parents[1]
APP_ROOT = Path(os.environ.get('ORBITAL_APP_ROOT', MAIL_ROOT.parent / 'orbital-app')).resolve()

CONFIG_FILES = (
    'apps/api/config/local/app.env',
    'apps/api/config/local/auth.env',
    'apps/api/config/local/database.env',
    'apps/api/config/local/services.env',
    'apps/api/config/production/app.env',
    'apps/api/config/production/auth.env',
    'apps/api/config/production/database.env',
    'apps/api/config/production/services.env',
    'apps/web/config/local/app.env',
    'apps/web/config/local/services.env',
    'apps/web/config/production/app.env',
    'apps/web/config/production/services.env',
)

# Diferenças funcionais intencionais. Qualquer exclusividade nova deve ser
# conscientemente adicionada aqui; caso contrário, o contrato falha.
APP_ONLY_PREFIXES = {
    'apps/api/config/local/database.env': ('MARIADB_',),
    'apps/api/config/production/database.env': ('MARIADB_',),
}

APP_ONLY_KEYS = {
    'apps/api/config/local/app.env': {
        'APEX_APPLICATION_ID', 'APEX_MENU_LIST', 'APP_DEBUG_DETAILS',
        'DEV_MONITOR_DISK_PATH', 'DEV_MONITOR_NGINX_ACCESS_LOG',
        'DEV_MONITOR_NGINX_ERROR_LOG', 'DEV_MONITOR_SYSTEMD_UNITS',
        'ERROR_LOG_DIR', 'ERROR_LOG_ENABLED', 'ERROR_LOG_RETENTION_DAYS',
        'NOTE_WORKER_BATCH_SIZE', 'NOTE_WORKER_POLL_SECONDS',
        'NOTE_WORKER_RECOVERY_SECONDS', 'NOTE_WORKER_STALE_SECONDS',
        'NOTE_WORKER_SYSTEMD_SERVICE', 'ORACLE_NOTE_WORKER_POOL_SIZE',
    },
    'apps/api/config/production/app.env': {
        'APEX_APPLICATION_ID', 'APEX_MENU_LIST', 'APP_DEBUG_DETAILS',
        'DEV_MONITOR_DISK_PATH', 'DEV_MONITOR_NGINX_ACCESS_LOG',
        'DEV_MONITOR_NGINX_ERROR_LOG', 'DEV_MONITOR_SYSTEMD_UNITS',
        'ERROR_LOG_DIR', 'ERROR_LOG_ENABLED', 'ERROR_LOG_RETENTION_DAYS',
        'NOTE_WORKER_BATCH_SIZE', 'NOTE_WORKER_POLL_SECONDS',
        'NOTE_WORKER_RECOVERY_SECONDS', 'NOTE_WORKER_STALE_SECONDS',
        'NOTE_WORKER_SYSTEMD_SERVICE', 'ORACLE_NOTE_WORKER_POOL_SIZE',
    },
    'apps/api/config/local/auth.env': {
        'AUTH_SESSION_SECRET', 'SSO_CLIENT_ID', 'SSO_CLIENT_SECRET', 'SSO_REDIRECT_URIS',
    },
    'apps/api/config/production/auth.env': {
        'AUTH_SESSION_SECRET', 'SSO_CLIENT_ID', 'SSO_CLIENT_SECRET', 'SSO_REDIRECT_URIS',
    },
    'apps/web/config/local/services.env': {'REPORTS_API_URL', 'REPORTS_WEB_URL'},
    'apps/web/config/production/services.env': {'REPORTS_API_URL', 'REPORTS_WEB_URL'},
}

MAIL_ONLY_KEYS = {
    'apps/api/config/local/auth.env': {
        'AUTH_CONTEXT_URL', 'AUTH_MODE', 'AUTH_TIMEOUT_SECONDS',
    },
    'apps/api/config/production/auth.env': {
        'AUTH_CONTEXT_URL', 'AUTH_MODE', 'AUTH_TIMEOUT_SECONDS',
    },
    'apps/api/config/local/services.env': {
        'EMAIL_FROM_ADDRESS', 'EMAIL_FROM_NAME', 'EMAIL_PROVIDER', 'EMAIL_REPLY_TO',
        'EMAIL_SEND_ENABLED', 'EMAIL_SEND_TIMEOUT_SECONDS', 'EMAIL_TEST_MAX_MESSAGES',
        'EMAIL_TEST_MAX_RECIPIENTS', 'EMAIL_TEST_MAX_REPETITIONS',
        'EMAIL_TEST_MAX_WORKERS', 'EMAIL_UPLOAD_DIR', 'EMAIL_UPLOAD_MAX_BYTES',
        'EMAIL_UPLOAD_PUBLIC_URL', 'EMAIL_WORKER_DELAY_MS', 'EMAIL_WORKER_MAX_ATTEMPTS',
        'MAIL_PUBLIC_URL', 'MAIL_UNSUBSCRIBE_SECRET', 'SMTP2GO_API_KEY',
        'SMTP2GO_API_URL', 'SMTP_HOST', 'SMTP_PASSWORD', 'SMTP_PORT',
        'SMTP_SECURITY', 'SMTP_USERNAME',
    },
    'apps/web/config/local/services.env': {'PUBLIC_ORBITAL_HOME_URL'},
    'apps/web/config/production/services.env': {'PUBLIC_ORBITAL_HOME_URL'},
    'apps/api/config/production/services.env': {
        'EMAIL_FROM_ADDRESS', 'EMAIL_FROM_NAME', 'EMAIL_PROVIDER', 'EMAIL_REPLY_TO',
        'EMAIL_SEND_ENABLED', 'EMAIL_SEND_TIMEOUT_SECONDS', 'EMAIL_TEST_MAX_MESSAGES',
        'EMAIL_TEST_MAX_RECIPIENTS', 'EMAIL_TEST_MAX_REPETITIONS',
        'EMAIL_TEST_MAX_WORKERS', 'EMAIL_UPLOAD_DIR', 'EMAIL_UPLOAD_MAX_BYTES',
        'EMAIL_UPLOAD_PUBLIC_URL', 'EMAIL_WORKER_DELAY_MS', 'EMAIL_WORKER_MAX_ATTEMPTS',
        'MAIL_PUBLIC_URL', 'MAIL_UNSUBSCRIBE_SECRET', 'SMTP2GO_API_KEY',
        'SMTP2GO_API_URL', 'SMTP_HOST', 'SMTP_PASSWORD', 'SMTP_PORT',
        'SMTP_SECURITY', 'SMTP_USERNAME',
    },
}


def env_keys(root: Path, rel: str) -> list[str]:
    lines = (root / rel).read_text(encoding='utf-8').splitlines()
    return [line.split('=', 1)[0] for line in lines if line]


def env_map(root: Path, rel: str) -> dict[str, str]:
    result = {}
    for line in (root / rel).read_text(encoding='utf-8').splitlines():
        if line:
            key, value = line.split('=', 1)
            result[key] = value
    return result


def allowed_app_only(rel: str, keys: set[str]) -> set[str]:
    allowed = set(APP_ONLY_KEYS.get(rel, set()))
    for prefix in APP_ONLY_PREFIXES.get(rel, ()):
        allowed.update(key for key in keys if key.startswith(prefix))
    return allowed


def test_orbital_app_reference_exists():
    assert APP_ROOT.is_dir(), (
        f'orbital-app não encontrado em {APP_ROOT}. '
        'Defina ORBITAL_APP_ROOT para o diretório do orbital-app.'
    )


def test_env_file_tree_is_1x1():
    app_files = {
        str(path.relative_to(APP_ROOT))
        for path in APP_ROOT.glob('apps/*/config/*/*.env')
    }
    mail_files = {
        str(path.relative_to(MAIL_ROOT))
        for path in MAIL_ROOT.glob('apps/*/config/*/*.env')
    }
    assert app_files == set(CONFIG_FILES)
    assert mail_files == set(CONFIG_FILES)
    assert mail_files == app_files


def test_local_and_production_have_same_file_and_key_structure():
    for root in (APP_ROOT, MAIL_ROOT):
        for app in ('api', 'web'):
            local_dir = root / f'apps/{app}/config/local'
            production_dir = root / f'apps/{app}/config/production'
            local_files = sorted(path.name for path in local_dir.glob('*.env'))
            production_files = sorted(path.name for path in production_dir.glob('*.env'))
            assert local_files == production_files
            for name in local_files:
                local_rel = f'apps/{app}/config/local/{name}'
                production_rel = f'apps/{app}/config/production/{name}'
                assert env_keys(root, local_rel) == env_keys(root, production_rel)


def test_shared_variables_are_in_same_file_and_same_relative_order():
    for rel in CONFIG_FILES:
        app_keys = env_keys(APP_ROOT, rel)
        mail_keys = env_keys(MAIL_ROOT, rel)
        shared = set(app_keys) & set(mail_keys)
        assert [key for key in app_keys if key in shared] == [key for key in mail_keys if key in shared], rel


def test_exclusive_variables_are_only_the_documented_differences():
    for rel in CONFIG_FILES:
        app_keys = set(env_keys(APP_ROOT, rel))
        mail_keys = set(env_keys(MAIL_ROOT, rel))
        app_only = app_keys - mail_keys
        mail_only = mail_keys - app_keys
        assert app_only == allowed_app_only(rel, app_keys), f'{rel}: app-only inesperado: {sorted(app_only)}'
        assert mail_only == MAIL_ONLY_KEYS.get(rel, set()), f'{rel}: mail-only inesperado: {sorted(mail_only)}'


def test_same_variable_never_moves_to_another_env_file():
    for context in ('local', 'production'):
        for app in ('api', 'web'):
            def locations(root: Path):
                found = {}
                for path in sorted((root / f'apps/{app}/config/{context}').glob('*.env')):
                    for key in env_keys(root, str(path.relative_to(root))):
                        found[key] = path.name
                return found

            app_locations = locations(APP_ROOT)
            mail_locations = locations(MAIL_ROOT)
            for key in set(app_locations) & set(mail_locations):
                assert app_locations[key] == mail_locations[key], (
                    f'{app}/{context}: {key} está em {app_locations[key]} no app '
                    f'e em {mail_locations[key]} no mail'
                )


def test_database_oracle_contract_is_identical_except_mariadb():
    for context in ('local', 'production'):
        rel = f'apps/api/config/{context}/database.env'
        app = env_map(APP_ROOT, rel)
        mail = env_map(MAIL_ROOT, rel)
        app_oracle = {k: v for k, v in app.items() if not k.startswith('MARIADB_')}
        assert mail == app_oracle
