from functools import lru_cache
from pathlib import Path
from typing import Annotated

from pydantic import field_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict

API_DIR = Path(__file__).resolve().parents[1]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=API_DIR / ".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    app_name: str = "Orbital Mail API"
    app_env: str = "development"
    app_host: str = "0.0.0.0"
    app_port: int = 8102
    cors_origins: Annotated[list[str], NoDecode] = [
        "http://localhost:4102",
        "http://127.0.0.1:4102",
    ]

    oracle_user: str = ""
    oracle_password: str = ""
    oracle_connect_string: str = "localhost:1521/FREEPDB1"
    oracle_wallet_local_dir: str | None = None
    oracle_wallet_remote_dir: str | None = None
    oracle_wallet_password: str | None = None
    oracle_current_schema: str = "ORBITAL_MAIL"
    oracle_pool_size: int = 3
    oracle_pool_max_overflow: int = 2
    oracle_pool_timeout_seconds: int = 10
    oracle_pool_recycle_seconds: int = 300
    oracle_pool_pre_ping: bool = True
    oracle_sql_echo: bool = False

    auth_mode: str = "remote"
    orbital_auth_context_url: str | None = None
    auth_timeout_seconds: float = 5.0

    # Contexto local simulado, usado somente quando AUTH_MODE=disabled.
    dev_tenant_code: str | None = None
    dev_user_id: int = 1
    dev_is_admin: bool = True

    mail_provider: str = "disabled"
    mail_send_enabled: bool = False
    mail_from_name: str = "Orbital Mail"
    mail_from_address: str | None = None
    mail_reply_to: str | None = None
    smtp_host: str | None = None
    smtp_port: int = 587
    smtp_username: str | None = None
    smtp_password: str | None = None
    smtp_security: str = "tls"
    smtp2go_api_key: str | None = None
    smtp2go_api_url: str = "https://api.smtp2go.com/v3/email/send"
    mail_send_timeout_seconds: float = 30.0
    mail_worker_delay_ms: int = 200
    mail_worker_max_attempts: int = 3
    mail_test_max_workers: int = 5
    mail_test_max_recipients: int = 100
    mail_test_max_repetitions: int = 5
    mail_test_max_messages: int = 300

    mail_upload_dir: str = "/home/daniel/Code/data/orbital-mail/uploads"
    mail_public_upload_url: str = "http://127.0.0.1:8102/uploads/mail"
    mail_upload_max_bytes: int = 5_242_880

    @field_validator("cors_origins", mode="before")
    @classmethod
    def parse_csv(cls, value):
        if isinstance(value, str):
            return [item.strip() for item in value.split(",") if item.strip()]
        return value

    @field_validator("smtp_security")
    @classmethod
    def validate_smtp_security(cls, value: str) -> str:
        normalized = value.strip().lower()
        if normalized not in {"none", "tls", "ssl"}:
            raise ValueError("SMTP_SECURITY deve ser none, tls ou ssl.")
        return normalized

    @field_validator("auth_mode")
    @classmethod
    def validate_auth_mode(cls, value: str) -> str:
        normalized = value.strip().lower()
        if normalized not in {"disabled", "remote"}:
            raise ValueError("AUTH_MODE deve ser 'disabled' ou 'remote'.")
        return normalized


@lru_cache
def get_settings() -> Settings:
    return Settings()
