import json

import pytest

from core.settings import Settings
from routes import health as health_routes


def test_liveness_payload_contract():
    payload = health_routes.health()
    assert payload["status"] == "ok"
    assert payload["service"].endswith("-api")
    assert payload["environment"]


def test_readiness_payload_contract(monkeypatch):
    monkeypatch.setattr(
        health_routes,
        "check_database_health",
        lambda: {"ok": True, "provider": "oracle", "latency_ms": 1.25},
    )
    response = health_routes.health_db()
    payload = json.loads(response.body)
    assert response.status_code == 200
    assert payload["database"] == {
        "provider": "oracle",
        "status": "ok",
        "latency_ms": 1.25,
    }


def test_readiness_returns_503_without_leaking_error(monkeypatch):
    monkeypatch.setattr(
        health_routes,
        "check_database_health",
        lambda: {
            "ok": False,
            "provider": "oracle",
            "latency_ms": 2.5,
            "error_type": "OperationalError",
        },
    )
    response = health_routes.health_db()
    payload = json.loads(response.body)
    assert response.status_code == 503
    assert response.headers["retry-after"] == "2"
    assert payload["database"]["error_type"] == "OperationalError"
    assert "password" not in response.body.decode().lower()


def test_cors_rejects_json_format():
    with pytest.raises(ValueError, match="CSV simples"):
        Settings(_env_file=None, APP_CORS_ORIGINS='["http://localhost:4101"]')


def test_production_requires_remote_auth_and_oracle():
    with pytest.raises(ValueError, match="AUTH_MODE deve ser remote"):
        Settings(_env_file=None, APP_ENV="production", AUTH_MODE="disabled")


def test_worker_readiness_reports_send_switch_without_sending(monkeypatch):
    class DummySession:
        def close(self):
            pass

    class DummyFactory:
        def __call__(self):
            return DummySession()

    monkeypatch.setattr(health_routes, "get_session_factory", lambda: DummyFactory())
    monkeypatch.setattr(health_routes.MailDeliveryWorkerService, "check_readiness", lambda self: None)

    response = health_routes.health_worker()
    payload = json.loads(response.body)
    assert response.status_code == 200
    assert payload["worker"]["status"] == "ok"
    assert payload["worker"]["send_enabled"] is False
    assert payload["worker"]["provider"] == "smtp2go"


def test_worker_readiness_returns_503_for_missing_schema(monkeypatch):
    class DummySession:
        def close(self):
            pass

    class DummyFactory:
        def __call__(self):
            return DummySession()

    monkeypatch.setattr(health_routes, "get_session_factory", lambda: DummyFactory())

    def missing(_self):
        raise health_routes.MailSendWorkerSchemaMissingError("schema mail ausente")

    monkeypatch.setattr(health_routes.MailDeliveryWorkerService, "check_readiness", missing)
    response = health_routes.health_worker()
    payload = json.loads(response.body)
    assert response.status_code == 503
    assert response.headers["retry-after"] == "2"
    assert payload["worker"]["error_type"] == "MailSendWorkerSchemaMissingError"
    assert payload["worker"]["detail"] == "schema mail ausente"
