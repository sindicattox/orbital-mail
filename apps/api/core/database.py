from __future__ import annotations

from collections.abc import Generator
import logging
import re
from time import monotonic, sleep
from typing import Any

from sqlalchemy import create_engine, event, text
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from core.settings import Settings, get_settings


logger = logging.getLogger("app.database")
_ORACLE_CONNECT_RECOVERY_PATTERN = re.compile(
    r"(?:DPY-4011|DPY-6005|"
    r"ORA-01033|ORA-03113|ORA-03114|ORA-03135|"
    r"ORA-12170|ORA-12514|ORA-12535|ORA-12537|ORA-12541|"
    r"ORA-12545|ORA-12547|ORA-12570|ORA-12571)",
    re.IGNORECASE,
)


def build_oracle_connect_arguments(settings: Settings) -> dict[str, Any]:
    arguments: dict[str, Any] = {
        "user": settings.oracle_user,
        "password": settings.oracle_password,
        "dsn": settings.oracle_connect_string,
        "tcp_connect_timeout": settings.oracle_tcp_connect_timeout_seconds,
        "retry_count": settings.oracle_connect_retry_count,
        "retry_delay": settings.oracle_connect_retry_delay_seconds,
        "expire_time": settings.oracle_expire_time_minutes,
    }
    wallet_dir = settings.oracle_wallet_dir.strip()
    if wallet_dir:
        arguments["config_dir"] = wallet_dir
        arguments["wallet_location"] = wallet_dir
    if settings.oracle_wallet_password.strip():
        arguments["wallet_password"] = settings.oracle_wallet_password
    return arguments


def create_oracle_connection(settings: Settings):
    import oracledb

    required = {
        "ORACLE_USER": settings.oracle_user,
        "ORACLE_PASSWORD": settings.oracle_password,
        "ORACLE_CONNECT_STRING": settings.oracle_connect_string,
    }
    missing = [name for name, value in required.items() if not str(value or "").strip()]
    if missing:
        raise RuntimeError(f"Configuração Oracle obrigatória ausente: {', '.join(missing)}.")

    arguments = build_oracle_connect_arguments(settings)
    maximum_attempts = 1 + settings.oracle_connect_recovery_attempts
    for attempt in range(1, maximum_attempts + 1):
        try:
            connection = oracledb.connect(**arguments)
            connection.call_timeout = settings.oracle_call_timeout_ms
            return connection
        except Exception as error:
            recovery_match = _ORACLE_CONNECT_RECOVERY_PATTERN.search(str(error))
            if attempt >= maximum_attempts or recovery_match is None:
                raise
            logger.warning(
                "[DB-CONNECT] abertura Oracle transitória falhou code=%s type=%s; nova tentativa=%s/%s em %ss",
                recovery_match.group(0).upper(),
                type(error).__name__,
                attempt + 1,
                maximum_attempts,
                settings.oracle_connect_retry_delay_seconds,
            )
            sleep(settings.oracle_connect_retry_delay_seconds)

    raise RuntimeError("Fluxo impossível ao abrir conexão Oracle.")


def _configure_oracle_engine(engine: Engine, settings: Settings) -> None:
    schema = settings.oracle_current_schema.strip().upper()
    if schema and not re.fullmatch(r"[A-Z][A-Z0-9_$#]*", schema):
        raise ValueError("ORACLE_CURRENT_SCHEMA inválido.")

    @event.listens_for(engine, "connect")
    def configure_oracle_session(dbapi_connection, _connection_record):
        dbapi_connection.call_timeout = settings.oracle_call_timeout_ms
        if not schema:
            return
        cursor = dbapi_connection.cursor()
        try:
            cursor.execute(f"ALTER SESSION SET CURRENT_SCHEMA = {schema}")
            cursor.execute("ALTER SESSION DISABLE PARALLEL DML")
        finally:
            cursor.close()


_engine: Engine | None = None


def get_engine() -> Engine:
    global _engine
    if _engine is not None:
        return _engine

    settings = get_settings()
    _engine = create_engine(
        "oracle+oracledb://",
        creator=lambda: create_oracle_connection(settings),
        pool_pre_ping=settings.oracle_pool_pre_ping,
        pool_use_lifo=settings.oracle_pool_use_lifo,
        pool_size=settings.oracle_pool_size,
        max_overflow=settings.oracle_pool_max_overflow,
        pool_timeout=settings.oracle_pool_timeout_seconds,
        pool_recycle=settings.oracle_pool_recycle_seconds if settings.oracle_pool_recycle_seconds > 0 else -1,
        pool_reset_on_return="rollback",
        echo=settings.db_sql_echo and settings.app_env == "development",
    )
    _configure_oracle_engine(_engine, settings)
    return _engine


_session_factory = None


def get_session_factory():
    global _session_factory
    if _session_factory is None:
        _session_factory = sessionmaker(
            bind=get_engine(),
            autocommit=False,
            autoflush=False,
            expire_on_commit=False,
        )
    return _session_factory


def get_db() -> Generator[Session, None, None]:
    db = get_session_factory()()
    try:
        yield db
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def check_database_health() -> dict:
    started_at = monotonic()
    try:
        with get_engine().connect() as connection:
            value = connection.execute(text("SELECT 1 FROM DUAL")).scalar_one()
        return {
            "ok": value == 1,
            "provider": "oracle",
            "latency_ms": round((monotonic() - started_at) * 1000, 2),
        }
    except Exception as error:
        return {
            "ok": False,
            "provider": "oracle",
            "latency_ms": round((monotonic() - started_at) * 1000, 2),
            "error_type": type(error).__name__,
        }
