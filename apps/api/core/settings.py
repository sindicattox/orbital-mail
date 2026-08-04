from functools import lru_cache
from pathlib import Path
from typing import Annotated
from urllib.parse import urlparse, urlunparse

from pydantic import Field, field_validator, model_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict

API_DIR = Path(__file__).resolve().parents[1]
API_ENV_FILE = API_DIR / ".env"
PRODUCTION_ENVS = {"production", "prod", "remote"}
PUBLIC_UPLOAD_PATH = "/api/mail/uploads"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=API_ENV_FILE,
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
        populate_by_name=True,
    )

    app_name: str = Field("Orbital Mail API", validation_alias="APP_NAME")
    app_service: str = Field("orbital-mail-api", validation_alias="APP_SERVICE")
    app_env: str = Field("development", validation_alias="APP_ENV")
    app_host: str = Field("0.0.0.0", validation_alias="APP_HOST")
    app_port: int = Field(8104, validation_alias="APP_PORT")
    cors_origins: Annotated[list[str], NoDecode] = Field(
        ['http://localhost:4104', 'http://127.0.0.1:4104', 'http://localhost:4001', 'http://127.0.0.1:4001'],
        validation_alias="APP_CORS_ORIGINS",
    )

    # standalone: contexto integralmente vindo de AUTH_DEV_*.
    # remote: contexto autenticado recebido do orbital-app via AUTH_CONTEXT_URL.
    auth_mode: str = Field("standalone", validation_alias="AUTH_MODE")
    auth_context_url: str | None = Field(None, validation_alias="AUTH_CONTEXT_URL")
    auth_timeout_seconds: float = Field(5.0, validation_alias="AUTH_TIMEOUT_SECONDS")
    dev_tenant_code: str | None = Field("anpprev", validation_alias="AUTH_DEV_TENANT_CODE")
    dev_user_id: int = Field(1, ge=1, validation_alias="AUTH_DEV_USER_ID")
    dev_is_admin: bool = Field(True, validation_alias="AUTH_DEV_IS_ADMIN")

    oracle_user: str | None = Field(None, validation_alias="ORACLE_USER")
    oracle_password: str | None = Field(None, validation_alias="ORACLE_PASSWORD")
    oracle_connect_string: str | None = Field(None, validation_alias="ORACLE_CONNECT_STRING")
    oracle_wallet_local_dir: str | None = Field(None, validation_alias="ORACLE_WALLET_LOCAL_DIR")
    oracle_wallet_remote_dir: str | None = Field(None, validation_alias="ORACLE_WALLET_REMOTE_DIR")
    oracle_wallet_password: str | None = Field(None, validation_alias="ORACLE_WALLET_PASSWORD")
    oracle_current_schema: str | None = Field(None, validation_alias="ORACLE_CURRENT_SCHEMA")
    oracle_pool_size: int = Field(3, validation_alias="ORACLE_POOL_SIZE")
    oracle_pool_max_overflow: int = Field(2, validation_alias="ORACLE_POOL_MAX_OVERFLOW")
    oracle_pool_timeout_seconds: int = Field(10, validation_alias="ORACLE_POOL_TIMEOUT_SECONDS")
    oracle_pool_recycle_seconds: int = Field(300, validation_alias="ORACLE_POOL_RECYCLE_SECONDS")
    oracle_pool_pre_ping: bool = Field(True, validation_alias="ORACLE_POOL_PRE_PING")
    oracle_pool_use_lifo: bool = Field(True, validation_alias="ORACLE_POOL_USE_LIFO")
    oracle_sql_echo: bool = Field(False, validation_alias="DB_SQL_ECHO")

    mail_provider: str = Field("disabled", validation_alias="EMAIL_PROVIDER")
    mail_send_enabled: bool = Field(False, validation_alias="EMAIL_SEND_ENABLED")
    mail_from_name: str = Field("Orbital Mail", validation_alias="EMAIL_FROM_NAME")
    mail_from_address: str | None = Field(None, validation_alias="EMAIL_FROM_ADDRESS")
    mail_reply_to: str | None = Field(None, validation_alias="EMAIL_REPLY_TO")
    smtp_host: str | None = Field(None, validation_alias="SMTP_HOST")
    smtp_port: int = Field(587, validation_alias="SMTP_PORT")
    smtp_username: str | None = Field(None, validation_alias="SMTP_USERNAME")
    smtp_password: str | None = Field(None, validation_alias="SMTP_PASSWORD")
    smtp_security: str = Field("tls", validation_alias="SMTP_SECURITY")
    smtp2go_api_key: str | None = Field(None, validation_alias="SMTP2GO_API_KEY")
    smtp2go_api_url: str = Field("https://api.smtp2go.com/v3/email/send", validation_alias="SMTP2GO_API_URL")
    mail_send_timeout_seconds: float = Field(30.0, validation_alias="EMAIL_SEND_TIMEOUT_SECONDS")
    mail_worker_delay_ms: int = Field(200, validation_alias="EMAIL_WORKER_DELAY_MS")
    mail_worker_max_attempts: int = Field(3, validation_alias="EMAIL_WORKER_MAX_ATTEMPTS")
    mail_test_max_workers: int = Field(5, validation_alias="EMAIL_TEST_MAX_WORKERS")
    mail_test_max_recipients: int = Field(100, validation_alias="EMAIL_TEST_MAX_RECIPIENTS")
    mail_test_max_repetitions: int = Field(5, validation_alias="EMAIL_TEST_MAX_REPETITIONS")
    mail_test_max_messages: int = Field(300, validation_alias="EMAIL_TEST_MAX_MESSAGES")
    mail_upload_dir: str = Field("/home/daniel/Code/data/orbital-mail/uploads", validation_alias="EMAIL_UPLOAD_DIR")
    mail_public_upload_url: str = Field("http://127.0.0.1:8104/api/mail/uploads", validation_alias="EMAIL_UPLOAD_PUBLIC_URL")
    mail_upload_max_bytes: int = Field(5_242_880, validation_alias="EMAIL_UPLOAD_MAX_BYTES")
    mail_public_url: str = Field("http://127.0.0.1:4106", validation_alias="MAIL_PUBLIC_URL")
    mail_unsubscribe_secret: str | None = Field(None, validation_alias="MAIL_UNSUBSCRIBE_SECRET")

    @field_validator("cors_origins", mode="before")
    @classmethod
    def parse_cors_origins(cls, value):
        if isinstance(value, str):
            raw = value.strip()
            if not raw:
                return []
            if raw.startswith("[") or '"' in raw or "'" in raw:
                raise ValueError("APP_CORS_ORIGINS deve usar CSV simples, sem colchetes e sem aspas.")
            value = raw.split(",")
        if isinstance(value, (list, tuple, set)):
            return list(dict.fromkeys(str(item).strip().rstrip("/") for item in value if str(item).strip()))
        return value

    @field_validator("auth_mode")
    @classmethod
    def validate_auth_mode(cls, value: str) -> str:
        normalized = value.strip().lower()
        if normalized in {"disabled", "dev", "local"}:
            return "standalone"
        if normalized not in {"standalone", "remote"}:
            raise ValueError("AUTH_MODE deve ser standalone ou remote.")
        return normalized

    @field_validator("mail_public_upload_url")
    @classmethod
    def validate_mail_public_upload_url(cls, value: str) -> str:
        raw = str(value or "").strip().rstrip("/")
        parsed = urlparse(raw)
        if parsed.scheme not in {"http", "https"} or not parsed.netloc:
            raise ValueError(
                "EMAIL_UPLOAD_PUBLIC_URL deve ser uma URL absoluta HTTP/HTTPS, "
                f"terminando em {PUBLIC_UPLOAD_PATH}."
            )
        if parsed.params or parsed.query or parsed.fragment:
            raise ValueError("EMAIL_UPLOAD_PUBLIC_URL não pode conter parâmetros, query string ou fragmento.")
        if parsed.path.rstrip("/") != PUBLIC_UPLOAD_PATH:
            actual_path = parsed.path.rstrip("/") or "/"
            raise ValueError(
                "EMAIL_UPLOAD_PUBLIC_URL usa caminho incompatível: "
                f"{actual_path}. Use exatamente {PUBLIC_UPLOAD_PATH}."
            )
        return urlunparse((parsed.scheme, parsed.netloc, PUBLIC_UPLOAD_PATH, "", "", ""))

    @field_validator("smtp_security")
    @classmethod
    def validate_smtp_security(cls, value: str) -> str:
        normalized = value.strip().lower()
        if normalized not in {"none", "tls", "ssl"}:
            raise ValueError("SMTP_SECURITY deve ser none, tls ou ssl.")
        return normalized

    @model_validator(mode="after")
    def validate_mail_provider(self) -> "Settings":
        provider = self.mail_provider.strip().lower()
        if provider not in {"disabled", "smtp", "smtp2go"}:
            raise ValueError("EMAIL_PROVIDER deve ser disabled, smtp ou smtp2go.")
        self.mail_provider = provider
        if self.mail_send_enabled:
            if provider == "disabled":
                raise ValueError("EMAIL_PROVIDER não pode ser disabled quando EMAIL_SEND_ENABLED=true.")
            if provider == "smtp2go" and not str(self.smtp2go_api_key or "").strip():
                raise ValueError("SMTP2GO_API_KEY é obrigatória para EMAIL_PROVIDER=smtp2go.")
            if provider == "smtp" and not str(self.smtp_host or "").strip():
                raise ValueError("SMTP_HOST é obrigatório para EMAIL_PROVIDER=smtp.")
        return self

    @model_validator(mode="after")
    def validate_runtime_contract(self) -> "Settings":
        if self.auth_mode == "standalone" and not self.dev_tenant_code:
            raise ValueError("AUTH_DEV_TENANT_CODE é obrigatório quando AUTH_MODE=standalone.")
        if self.auth_mode == "remote" and not str(self.auth_context_url or "").strip():
            raise ValueError("AUTH_CONTEXT_URL é obrigatório quando AUTH_MODE=remote.")

        if self.app_env.strip().lower() in PRODUCTION_ENVS:
            missing = [
                name
                for name, value in {
                    "ORACLE_USER": self.oracle_user,
                    "ORACLE_PASSWORD": self.oracle_password,
                    "ORACLE_CONNECT_STRING": self.oracle_connect_string,
                    "ORACLE_WALLET_REMOTE_DIR": self.oracle_wallet_remote_dir,
                    "ORACLE_CURRENT_SCHEMA": self.oracle_current_schema,
                }.items()
                if not str(value or "").strip()
            ]
            if self.auth_mode != "remote":
                missing.append("AUTH_MODE=remote")
            if any("localhost" in origin or "127.0.0.1" in origin for origin in self.cors_origins):
                missing.append("APP_CORS_ORIGINS sem origens locais")
            public_upload_url = self.mail_public_upload_url.strip().lower()
            if not public_upload_url.startswith("https://"):
                missing.append("EMAIL_UPLOAD_PUBLIC_URL com HTTPS público")
            if "localhost" in public_upload_url or "127.0.0.1" in public_upload_url:
                missing.append("EMAIL_UPLOAD_PUBLIC_URL sem endereço local")
            if missing:
                raise ValueError(f"Configuração de produção incompleta: {', '.join(missing)}.")
        return self

    @property
    def oracle_wallet_dir(self) -> str | None:
        if self.app_env.strip().lower() in PRODUCTION_ENVS:
            return self.oracle_wallet_remote_dir or self.oracle_wallet_local_dir
        return self.oracle_wallet_local_dir or self.oracle_wallet_remote_dir


@lru_cache
def get_settings() -> Settings:
    return Settings()
