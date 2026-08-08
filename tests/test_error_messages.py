from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_api_registers_coherent_validation_and_database_errors():
    main = (ROOT / 'apps/api/main.py').read_text(encoding='utf-8')
    errors = (ROOT / 'apps/api/core/errors.py').read_text(encoding='utf-8')

    assert 'register_error_handlers(app)' in main
    assert 'RequestValidationError' in errors
    assert 'IntegrityError' in errors
    assert 'ApiErrorMiddleware' in errors
    assert 'Não foi possível acessar o banco de dados.' in errors
    assert 'Não foi possível concluir a operação.' in errors
    assert 'Não foi possível salvar porque já existe um registro com os mesmos dados.' in errors


def test_web_normalizes_api_and_connection_errors():
    layout = (ROOT / 'apps/web/src/layouts/AppLayout.astro').read_text(encoding='utf-8')
    helper = (ROOT / 'apps/web/public/scripts/api-errors.js').read_text(encoding='utf-8')
    component = (ROOT / 'apps/web/public/components/mail.js').read_text(encoding='utf-8')

    assert 'src={`${moduleBase}/scripts/api-errors.js`}' in layout
    assert 'Não foi possível conectar à API do Orbital Mail.' in helper
    assert 'fromResponse' in helper
    assert "import '../scripts/api-errors.js';" in component
    assert 'Failed to fetch' not in component


def test_pages_do_not_expose_raw_api_objects_as_messages():
    pages = ROOT / 'apps/web/src/pages'
    source = '\n'.join(path.read_text(encoding='utf-8') for path in pages.rglob('*.astro'))

    assert 'JSON.stringify(result.detail' not in source
    assert 'result.detail?.[0]?.msg' not in source
    assert 'Falha inesperada' not in source


def test_legacy_campaign_unique_constraint_has_idempotent_migration():
    migration = ROOT / 'database/oracle/003_drop_legacy_campaign_stats_unique.sql'
    source = migration.read_text(encoding='utf-8')

    assert 'DROP CONSTRAINT UK_EMAIL_CAMPAIGN_STATS' in source
    assert 'SQLCODE != -2443' in source


def test_unexpected_api_error_returns_json_with_cors():
    from fastapi import FastAPI
    from fastapi.middleware.cors import CORSMiddleware
    from fastapi.testclient import TestClient

    from core.errors import register_error_handlers

    app = FastAPI()
    register_error_handlers(app)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=['http://localhost:4106'],
        allow_credentials=True,
        allow_methods=['*'],
        allow_headers=['*'],
    )

    @app.get('/error')
    def raise_error():
        raise RuntimeError('erro técnico não exposto')

    response = TestClient(app, raise_server_exceptions=False).get(
        '/error',
        headers={'Origin': 'http://localhost:4106'},
    )

    assert response.status_code == 500
    assert response.json() == {
        'detail': 'Não foi possível concluir a operação. Tente novamente em instantes.',
    }
    assert response.headers['access-control-allow-origin'] == 'http://localhost:4106'
    assert 'erro técnico não exposto' not in response.text
