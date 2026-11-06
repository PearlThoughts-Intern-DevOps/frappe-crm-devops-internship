import logging
import sys
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import ClassVar


class ColorFormatter(logging.Formatter):
	COLORS: ClassVar[dict[int, str]] = {
		logging.DEBUG: "\033[36m",  # Cyan
		logging.INFO: "\033[32m",  # Green
		logging.WARNING: "\033[33m",  # Yellow
		logging.ERROR: "\033[31m",  # Red
		logging.CRITICAL: "\033[1;31m",  # Bold Red
	}
	RESET = "\033[0m"

	def format(self, record: logging.LogRecord) -> str:
		color = self.COLORS.get(record.levelno, self.RESET)
		levelname = f"{color}{record.levelname:<8}{self.RESET}"
		return f"{self.formatTime(record, '%Y-%m-%d %H:%M:%S')} | {levelname} | {record.getMessage()}"


def setup_logger(logs_dir: Path, quiet_console: bool = False) -> logging.Logger:
	logger = logging.getLogger("DockerMonitor")
	if logger.handlers:
		return logger

	logger.setLevel(logging.DEBUG)

	file_handler = RotatingFileHandler(
		logs_dir / "docker_monitor.log", maxBytes=5 * 1024 * 1024, backupCount=3
	)
	file_handler.setLevel(logging.DEBUG)
	file_handler.setFormatter(logging.Formatter("%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"))
	logger.addHandler(file_handler)

	if not quiet_console:
		console_handler = logging.StreamHandler(sys.stderr)
		console_handler.setLevel(logging.INFO)
		console_handler.setFormatter(ColorFormatter())
		logger.addHandler(console_handler)

	return logger
