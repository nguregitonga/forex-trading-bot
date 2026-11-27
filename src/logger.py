"""
Logging setup for the Forex Trading Bot.

Usage:
    from src.logger import get_logger
    logger = get_logger(__name__)
"""

import logging
import os
from logging.handlers import RotatingFileHandler
from pathlib import Path

_LOG_FORMAT = "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"
_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"
_configured = False


def _configure_root() -> None:
    """Configure the shared 'forex_bot' logger once (console + rotating file)."""
    global _configured
    if _configured:
        return

    level_name = os.getenv("FOREX_BOT_LOG_LEVEL", "INFO").upper()
    level = getattr(logging, level_name, logging.INFO)
    log_dir = Path(os.getenv("FOREX_BOT_LOG_DIR", "logs"))

    root = logging.getLogger("forex_bot")
    root.setLevel(level)
    root.propagate = False
    formatter = logging.Formatter(_LOG_FORMAT, _DATE_FORMAT)

    console = logging.StreamHandler()
    console.setFormatter(formatter)
    root.addHandler(console)

    try:
        log_dir.mkdir(parents=True, exist_ok=True)
        file_handler = RotatingFileHandler(
            log_dir / "forex_bot.log", maxBytes=5_000_000, backupCount=3, encoding="utf-8"
        )
        file_handler.setFormatter(formatter)
        root.addHandler(file_handler)
    except OSError:
        # Read-only filesystem etc. — console logging still works.
        pass

    _configured = True


def get_logger(name: str) -> logging.Logger:
    """Return a logger namespaced under 'forex_bot'."""
    _configure_root()
    if not name.startswith("forex_bot"):
        name = f"forex_bot.{name}"
    return logging.getLogger(name)
