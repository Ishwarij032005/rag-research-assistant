# utils/logger.py

import logging
import sys
from pathlib import Path
from datetime import datetime
from utils.config import LOGS_DIR


def get_logger(name: str) -> logging.Logger:
    """
    Returns a configured logger that writes to both
    console and a daily rotating log file.

    Usage:
        from utils.logger import get_logger
        logger = get_logger(__name__)
        logger.info("Index built successfully")
        logger.error("Failed to connect to MongoDB")
    """
    logger = logging.getLogger(name)

    if logger.handlers:
        return logger   # Already configured

    logger.setLevel(logging.DEBUG)

    formatter = logging.Formatter(
        "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )

    # ── Console handler ────────────────────────────────────────
    console = logging.StreamHandler(sys.stdout)
    console.setLevel(logging.INFO)
    console.setFormatter(formatter)
    logger.addHandler(console)

    # ── File handler ───────────────────────────────────────────
    today    = datetime.now().strftime("%Y-%m-%d")
    log_file = LOGS_DIR / f"{today}.log"
    fh       = logging.FileHandler(log_file, encoding="utf-8")
    fh.setLevel(logging.DEBUG)
    fh.setFormatter(formatter)
    logger.addHandler(fh)

    return logger