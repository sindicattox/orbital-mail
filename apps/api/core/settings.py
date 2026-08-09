from functools import lru_cache
from pathlib import Path
from typing import Annotated
from urllib.parse import urlparse, urlunparse

from pydantic import Field, field_validator, model_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict

from core.load_env import load_config_environment

load_config_environment(overwrite=False)

API_DIR = Path(__file__).resolve().parents[1]
PRODUCTION_ENVS = {"production", "prod", "remote"}
PUBLIC_UPLOAD_PATH = "/orbital-mail/api/mail/uploads"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        case_sensitive=False,
        extra="ignore",
        populate_by_name=True,
    )

    app_name: str = Field("Orbital Mail API", validation_alias="APP_NAME")
    app_service: str = Field("orbital-mail-api", validation_alias="APP_SERVICE")
    app_env: str = Field("production", validation_alias="APP_ENV")
    app_host: str = Field("127.0.0.1", validation_alias="APP_HOST")
    app_port: int = Field(8106, validation_alias="APP_PORT")
    cors_origins: Annotated[list[str], NoDecode] = Field([], validation_alias="APP_CORS_ORIGINS")

    # Autenticação obrigatória via contexto central do orbital-app em todos os ambientes.
    auth_mode: str = Field("remote", validation_alias="AUTH_MODE")
    auth_context_url: str | None = Field(None, validation_alias="AUTH_CONTEXT_URL")
    auth_timeout_seconds: float = Field(5.0, validation_alias="AUTH_TIMEOUT_SECONDS")

    db_provider: str = Field("oracle", validation_alias="DB_PROVIDER")
    db_sql_echo: bool = Field(False, validation_alias="DB_SQL_ECHO")

    oracle_user: str = Field("", validation_alias="ORACLE_USER")
    oracle_password: str = Field("", validation_alias="ORACLE_PASSWORD")
    oracle_connect_string: str = Field("", validation_alias="ORACLE_CONNECT_STRING")
    oracle_wallet_dir: str = Field("", validation_alias="ORACLE_WALLET_DIR")
    oracle_wallet_password: str = Field("", validation_alias="ORACLE_WALLET_PASSWORD")
    oracle_current_schema: str = Field("", validation_alias="ORACLE_CURRENT_SCHEMA")

    oracle_pool_size: int = Field(2, validation_alias="ORACLE_POOL_SIZE")
    oracle_pool_max_overflow: int = Field(4, validation_alias="ORACLE_POOL_MAX_OVERFLOW")
    oracle_pool_timeout_seconds: int = Field(5, validation_alias="ORACLE_POOL_TIMEOUT_SECONDS")
    oracle_pool_recycle_seconds: int = Field(1800, validation_alias="ORACLE_POOL_RECYCLE_SECONDS")
    oracle_pool_pre_ping: bool = Field(True, validation_alias="ORACLE_POOL_PRE_PING")
    oracle_pool_use_lifo: bool = Field(True, validation_alias="ORACLE_POOL_USE_LIFO")

    oracle_tcp_connect_timeout_seconds: float = Field(5.0, validation_alias="ORACLE_TCP_CONNECT_TIMEOUT_SECONDS")
    oracle_connect_retry_count: int = Field(1, validation_alias="ORACLE_CONNECT_RETRY_COUNT")
    oracle_connect_retry_delay_seconds: int = Field(1, validation_alias="ORACLE_CONNECT_RETRY_DELAY_SECONDS")
    oracle_connect_recovery_attempts: int = Field(1, validation_alias="ORACLE_CONNECT_RECOVERY_ATTEMPTS")
    oracle_expire_time_minutes: int = Field(2, validation_alias="ORACLE_EXPIRE_TIME_MINUTES")
    oracle_call_timeout_ms: int = Field(15000, validation_alias="ORACLE_CALL_TIMEOUT_MS")
    oracle_pool_warn_checkout_seconds: float = Field(5.0, validation_alias="ORACLE_POOL_WARN_CHECKOUT_SECONDS")

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
    mail_public_upload_url: str = Field("", validation_alias="EMAIL_UPLOAD_PUBLIC_URL")
    mail_upload_max_bytes: int = Field(5_242_880, validation_alias="EMAIL_UPLOAD_MAX_BYTES")
    mail_public_url: str = Field("", validation_alias="MAIL_PUBLIC_URL")
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
        if normalized != "remote":
            raise ValueError("AUTH_MODE deve ser remote no orbital-mail.")
        return normalized

    @field_validator("db_provider")
    @classmethod
    def validate_db_provider(cls, value: str) -> str:
        provider = value.strip().lower()
        if provider != "oracle":
            raise ValueError("DB_PROVIDER deve ser oracle no orbital-mail.")
        return provider

    @field_validator("oracle_pool_size")
    @classmethod
    def validate_oracle_pool_size(cls, value: int) -> int:
        if not 1 <= value <= 30:
            raise ValueError("ORACLE_POOL_SIZE deve estar entre 1 e 30.")
        return value

    @field_validator("oracle_pool_max_overflow")
    @classmethod
    def validate_oracle_pool_max_overflow(cls, value: int) -> int:
        if not 0 <= value <= 30:
            raise ValueError("ORACLE_POOL_MAX_OVERFLOW deve estar entre 0 e 30.")
        return value

    @field_validator("oracle_pool_timeout_seconds", "oracle_pool_recycle_seconds")
    @classmethod
    def validate_oracle_pool_time_values(cls, value: int) -> int:
        if value < 0:
            raise ValueError("Os tempos do pool Oracle não podem ser negativos.")
        return value

    @field_validator("oracle_tcp_connect_timeout_seconds", "oracle_pool_warn_checkout_seconds")
    @classmethod
    def validate_oracle_positive_float_times(cls, value: float) -> float:
        if value <= 0:
            raise ValueError("Os limites de tempo Oracle devem ser maiores que zero.")
        return value

    @field_validator("oracle_connect_retry_count", "oracle_connect_recovery_attempts")
    @classmethod
    def validate_oracle_retry_count(cls, value: int) -> int:
        if not 0 <= value <= 5:
            raise ValueError("As tentativas de conexão Oracle devem estar entre 0 e 5.")
        return value

    @field_validator("oracle_expire_time_minutes")
    @classmethod
    def validate_oracle_expire_time(cls, value: int) -> int:
        if not 0 <= value <= 60:
            raise ValueError("ORACLE_EXPIRE_TIME_MINUTES deve estar entre 0 e 60.")
        return value

    @field_validator("oracle_connect_retry_delay_seconds")
    @classmethod
    def validate_oracle_retry_delay(cls, value: int) -> int:
        if not 0 <= value <= 10:
            raise ValueError("ORACLE_CONNECT_RETRY_DELAY_SECONDS deve estar entre 0 e 10.")
        return value

    @field_validator("oracle_call_timeout_ms")
    @classmethod
    def validate_oracle_call_timeout(cls, value: int) -> int:
        if value <= 0:
            raise ValueError("ORACLE_CALL_TIMEOUT_MS deve ser maior que zero.")
        return value

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
        if not str(self.auth_context_url or "").strip():
            raise ValueError("AUTH_CONTEXT_URL é obrigatório no orbital-mail.")

        if self.app_env.strip().lower() in PRODUCTION_ENVS:
            missing = [
                name
                for name, value in {
                    "ORACLE_USER": self.oracle_user,
                    "ORACLE_PASSWORD": self.oracle_password,
                    "ORACLE_CONNECT_STRING": self.oracle_connect_string,
                    "ORACLE_WALLET_DIR": self.oracle_wallet_dir,
                    "ORACLE_CURRENT_SCHEMA": self.oracle_current_schema,
                }.items()
                if not str(value or "").strip()
            ]
            if self.auth_mode != "remote":
                missing.append("AUTH_MODE=remote")
            if any((urlparse(origin).hostname or "").lower() in {"localhost", "127.0.0.1", "::1"} for origin in self.cors_origins):
                missing.append("APP_CORS_ORIGINS sem loopback direto")
            public_upload_url = self.mail_public_upload_url.strip()
            parsed_upload_url = urlparse(public_upload_url)
            if parsed_upload_url.scheme.lower() != "https":
                missing.append("EMAIL_UPLOAD_PUBLIC_URL com HTTPS público")
            if (parsed_upload_url.hostname or "").lower() in {"localhost", "127.0.0.1", "::1"}:
                missing.append("EMAIL_UPLOAD_PUBLIC_URL sem endereço local")
            if missing:
                raise ValueError(f"Configuração de produção incompleta: {', '.join(missing)}.")
        return self



@lru_cache
def get_settings() -> Settings:
    return Settings()
