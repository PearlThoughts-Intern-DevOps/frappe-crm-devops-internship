import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path
import sys


def setup_logger(log_file: Path, verbose: bool = False) -> logging.Logger:
    # Must match the package directory name ("backup_manager") so __name__ child loggers inherit handlers
    logger = logging.getLogger("BackupManager")
    logger.setLevel(logging.DEBUG)

    if logger.handlers:
        return logger

    log_file.parent.mkdir(parents=True, exist_ok=True)

    file_fmt = logging.Formatter(
        "%(asctime)s | %(levelname)-8s | %(name)s:%(funcName)s:%(lineno)d | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    file_handler = RotatingFileHandler(
        log_file, maxBytes=5 * 1024 * 1024, backupCount=5, encoding="utf-8"
    )
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(file_fmt)

    console_fmt = logging.Formatter(
        "%(asctime)s | %(levelname)-7s | %(message)s",
        datefmt="%H:%M:%S",
    )

    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.DEBUG if verbose else logging.INFO)
    console_handler.setFormatter(console_fmt)

    logger.addHandler(console_handler)
    logger.addHandler(file_handler)

    return logger