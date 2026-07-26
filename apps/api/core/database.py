from collections.abc import Generator
from functools import lru_cache
from time import monotonic
from urllib.parse import quote_plus

from sqlalchemy import create_engine, event, text
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from core.settings import get_settings


def _database_url() -> tuple[str, dict]:
    settings = get_settings()
    required = {
        "ORACLE_USER": settings.oracle_user,
        "ORACLE_PASSWORD": settings.oracle_password,
        "ORACLE_CONNECT_STRING": settings.oracle_connect_string,
    }
    missing = [name for name, value in required.items() if not str(value or "").strip()]
    if missing:
        raise RuntimeError(f"Configuração Oracle obrigatória ausente: {', '.join(missing)}.")

    connect_args: dict = {}
    wallet_dir = settings.oracle_wallet_dir
    if wallet_dir:
        connect_args.update(config_dir=wallet_dir, wallet_location=wallet_dir)
    if settings.oracle_wallet_password:
        connect_args["wallet_password"] = settings.oracle_wallet_password

    return (
        f"oracle+oracledb://{quote_plus(settings.oracle_user or '')}:"
        f"{quote_plus(settings.oracle_password or '')}@{settings.oracle_connect_string}",
        connect_args,
    )


@lru_cache
def get_engine() -> Engine:
    settings = get_settings()
    url, connect_args = _database_url()
    engine = create_engine(
        url,
        connect_args=connect_args,
        pool_pre_ping=settings.oracle_pool_pre_ping,
        pool_use_lifo=settings.oracle_pool_use_lifo,
        pool_size=settings.oracle_pool_size,
        max_overflow=settings.oracle_pool_max_overflow,
        pool_timeout=settings.oracle_pool_timeout_seconds,
        pool_recycle=settings.oracle_pool_recycle_seconds,
        echo=settings.oracle_sql_echo and settings.app_env == "development",
        future=True,
    )

    schema = str(settings.oracle_current_schema or "").strip().upper()
    if schema:
        if not schema.replace("_", "").isalnum() or schema[0].isdigit():
            raise ValueError("ORACLE_CURRENT_SCHEMA inválido.")

        @event.listens_for(engine, "connect")
        def set_current_schema(dbapi_connection, _connection_record):
            cursor = dbapi_connection.cursor()
            try:
                cursor.execute(f"ALTER SESSION SET CURRENT_SCHEMA = {schema}")
            finally:
                cursor.close()

    return engine


@lru_cache
def get_session_factory():
    return sessionmaker(bind=get_engine(), autocommit=False, autoflush=False, expire_on_commit=False)


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
