from collections.abc import Generator
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session, sessionmaker
from core.settings import get_settings

settings = get_settings()
_engine = None
_SessionLocal = None

def get_engine():
    global _engine, _SessionLocal
    if _engine is None:
        if not settings.oracle_user or not settings.oracle_password:
            raise RuntimeError('ORACLE_USER e ORACLE_PASSWORD não configurados.')
        url = f'oracle+oracledb://{settings.oracle_user}:{settings.oracle_password}@{settings.oracle_connect_string}'
        connect_args = {}
        wallet = settings.oracle_wallet_local_dir or settings.oracle_wallet_remote_dir
        if wallet:
            connect_args['config_dir'] = wallet
            connect_args['wallet_location'] = wallet
            if settings.oracle_wallet_password:
                connect_args['wallet_password'] = settings.oracle_wallet_password
        _engine = create_engine(url, pool_size=settings.oracle_pool_size, max_overflow=settings.oracle_pool_max_overflow,
            pool_timeout=settings.oracle_pool_timeout_seconds, pool_recycle=settings.oracle_pool_recycle_seconds,
            pool_pre_ping=settings.oracle_pool_pre_ping, echo=settings.oracle_sql_echo, connect_args=connect_args)
        _SessionLocal = sessionmaker(bind=_engine, autoflush=False, autocommit=False)
    return _engine

def get_db() -> Generator[Session, None, None]:
    get_engine()
    db = _SessionLocal()
    try:
        if settings.oracle_current_schema:
            db.execute(text(f'ALTER SESSION SET CURRENT_SCHEMA = {settings.oracle_current_schema}'))
        yield db
    finally:
        db.close()
