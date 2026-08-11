from __future__ import annotations

import logging
import os
import signal
from threading import Event
from time import monotonic

from core.load_env import load_config_environment


def _configure_worker_pool_environment() -> None:
    """Isola o worker em um pool Oracle mínimo antes da criação do Engine."""
    config = load_config_environment(overwrite=False)
    worker_pool_size = str(config.get("ORACLE_MAIL_WORKER_POOL_SIZE") or "1").strip()
    if not worker_pool_size.isdigit() or not 1 <= int(worker_pool_size) <= 30:
        raise RuntimeError("ORACLE_MAIL_WORKER_POOL_SIZE ausente ou inválido na configuração da API.")
    os.environ["ORACLE_POOL_SIZE"] = worker_pool_size
    os.environ["ORACLE_POOL_MAX_OVERFLOW"] = "0"


_configure_worker_pool_environment()

from core.database import close_database_engine, get_session_factory
from core.settings import get_settings
from mail.delivery_worker_service import MailDeliveryWorkerService

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger("orbital-mail.send-worker")
stop_event = Event()


def stop(*_args) -> None:
    stop_event.set()


def _positive_float(name: str, default: str, minimum: float) -> float:
    raw = str(os.getenv(name, default)).strip()
    try:
        value = float(raw)
    except ValueError as exc:
        raise RuntimeError(f"{name} inválido.") from exc
    if value < minimum:
        raise RuntimeError(f"{name} deve ser >= {minimum}.")
    return value


def _positive_int(name: str, default: str, minimum: int) -> int:
    raw = str(os.getenv(name, default)).strip()
    if not raw.isdigit() or int(raw) < minimum:
        raise RuntimeError(f"{name} inválido.")
    return int(raw)


def run() -> None:
    signal.signal(signal.SIGINT, stop)
    signal.signal(signal.SIGTERM, stop)
    settings = get_settings()
    poll_seconds = _positive_float("MAIL_WORKER_POLL_SECONDS", "5", 1.0)
    stale_seconds = _positive_int("MAIL_WORKER_STALE_SECONDS", "900", 60)
    recovery_seconds = _positive_float("MAIL_WORKER_RECOVERY_SECONDS", "60", 10.0)
    next_recovery_at = 0.0
    disabled_logged = False

    try:
        startup_db = get_session_factory()()
        try:
            MailDeliveryWorkerService(startup_db, settings).check_readiness()
        finally:
            startup_db.close()

        logger.info(
            "Worker de e-mail iniciado: provider=%s poll=%ss stale=%ss recovery=%ss pool=%s+0",
            settings.mail_provider,
            poll_seconds,
            stale_seconds,
            recovery_seconds,
            os.environ["ORACLE_POOL_SIZE"],
        )

        while not stop_event.is_set():
            db = get_session_factory()()
            should_wait = False
            try:
                service = MailDeliveryWorkerService(db, settings)
                now = monotonic()
                if now >= next_recovery_at:
                    recovered = service.recover_stale(stale_seconds)
                    if recovered:
                        logger.warning("Itens de e-mail abandonados recuperados: %s", recovered)
                    next_recovery_at = now + recovery_seconds

                if not settings.mail_send_enabled:
                    if not disabled_logged:
                        logger.info("Envio permanece bloqueado por EMAIL_SEND_ENABLED=false.")
                        disabled_logged = True
                    should_wait = True
                else:
                    disabled_logged = False
                    decision = service.process_one(settings.mail_provider)
                    if decision is None:
                        completed = service.finalize_completed_campaigns()
                        if completed:
                            logger.info("Campanhas finalizadas: %s", completed)
                        should_wait = True
                    elif settings.mail_worker_delay_ms > 0:
                        stop_event.wait(settings.mail_worker_delay_ms / 1000)
            except Exception:
                logger.exception("Falha no worker de envio de e-mail")
                try:
                    if db.in_transaction():
                        db.rollback()
                except Exception:
                    logger.exception("Falha ao desfazer transação do worker")
                should_wait = True
            finally:
                db.close()

            if should_wait:
                stop_event.wait(poll_seconds)
    finally:
        close_database_engine()
        logger.info("Worker de e-mail encerrado")


if __name__ == "__main__":
    run()
