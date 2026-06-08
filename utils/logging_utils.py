from datetime import timedelta, date, datetime, timezone
import logging
import os
from pathlib import Path
from typing import Optional
from zoneinfo import ZoneInfo

LOG_FORMAT = "%(asctime)s | %(levelname)s | %(name)s | %(message)s"
DATE_FORMAT = "%Y-%m-%d %H:%M:%S"
_LOG_CONFIGURED = False
TARGET_TIMEZONE = ZoneInfo("America/Sao_Paulo") # Este é o UTC-3 (ou UTC-2 no horário de verão)

class TimezoneFormatter(logging.Formatter):
    def __init__(self, fmt, datefmt, tzinfo):
        super().__init__(fmt=fmt, datefmt=datefmt)
        self.tzinfo = tzinfo

    def formatTime(self, record, datefmt=None):
        dt_utc = datetime.fromtimestamp(record.created, tz=timezone.utc)

        dt_target = dt_utc.astimezone(self.tzinfo)

        if datefmt:
            return dt_target.strftime(datefmt)

        return dt_target.strftime(self.default_time_format)


def yesterday(tz: str = "America/Sao_Paulo") -> date:
    return (datetime.now(ZoneInfo(tz)) - timedelta(days=1)).date()

def setup_logging(
    *, level: Optional[str] = None, log_file: Optional[str] = None
) -> None:
    global _LOG_CONFIGURED
    if _LOG_CONFIGURED:
        return

    level_name = (level or os.getenv("LOG_LEVEL", "INFO")).upper()
    log_level = getattr(logging, level_name, logging.INFO)

    formatter = TimezoneFormatter(
        fmt=LOG_FORMAT,
        datefmt=DATE_FORMAT,
        tzinfo=TARGET_TIMEZONE,  # Passa o objeto ZoneInfo
    )

    handlers = [logging.StreamHandler()]

    if log_file:
        log_path = Path(log_file)
        log_path.parent.mkdir(parents=True, exist_ok=True)
        # Cria o FileHandler e define o formatter
        file_handler = logging.FileHandler(log_path, encoding="utf-8")
        file_handler.setFormatter(formatter)
        handlers.append(file_handler)

    # Note que logging.basicConfig não aceita 'formatter',
    # então definimos o formatter explicitamente para cada handler.
    for handler in handlers:
        handler.setFormatter(formatter)

    logging.basicConfig(
        level=log_level,
        handlers=handlers,
    )

    _LOG_CONFIGURED = True


def get_logger(name: str) -> logging.Logger:
    """Simple helper so modules do not touch logging.getLogger directly."""
    return logging.getLogger(name)


def log_current_step(step_name: str, logger: Optional[logging.Logger] = None) -> None:
    log = logger or get_logger(__name__)
    log.info("=" * 60)
    log.info(f"--- {step_name} ---")
    log.info("=" * 60)
