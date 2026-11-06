import logging
from pathlib import Path
import shutil
import subprocess
import time

from .config import BackupConfig
from .exception import BenchCommandError

logger = logging.getLogger(__name__)


class BenchRunner:
    """Executes Frappe Bench commands natively or delegated via Docker."""

    def __init__(self, config: BackupConfig):
        self.config = config
        self.bench_bin: str | None = shutil.which("bench")

        # Fallback for cron environments where ~/.local/bin isn't in PATH
        if self.bench_bin is None and Path("/home/frappe/.local/bin/bench").is_file():
            self.bench_bin = "/home/frappe/.local/bin/bench"

        if self.bench_bin is not None:
            self.is_native = True
            logger.debug("Environment: Native Bench CLI detected at %s.", self.bench_bin)
        elif self.config.container_name and shutil.which("docker") is not None:
            self.is_native = False
            logger.debug(
                "Environment: Native bench not found. Delegating to Docker container '%s'.",
                self.config.container_name,
            )
        else:
            raise BenchCommandError(
                "Neither native 'bench' CLI nor 'docker' CLI was found in PATH."
            )

    @staticmethod
    def _sanitize_args(args: list[str]) -> str:
        """Masks sensitive password flags before logging commands."""
        sanitized = list(args)
        secret_flags = {"--mariadb-root-password", "--admin-password", "--db-password"}
        for i, arg in enumerate(sanitized):
            if arg in secret_flags and i + 1 < len(sanitized):
                sanitized[i + 1] = "***"
        return " ".join(sanitized)

    def execute(
        self, bench_args: list[str], timeout: int = 600
    ) -> subprocess.CompletedProcess:
        """Executes a bench command with timeout and automatic error handling."""
        if self.is_native:
            assert self.bench_bin is not None
            cmd = [self.bench_bin, *bench_args]
            cwd = self.config.bench_path
        else:
            assert self.config.container_name is not None
            cmd = [
                "docker",
                "exec",
                "-w",
                str(self.config.container_bench_path),
                self.config.container_name,
                "bench",
                *bench_args,
            ]
            cwd = None

        safe_cmd_str = self._sanitize_args(cmd)
        logger.debug("Executing: %s", safe_cmd_str)

        start_time = time.monotonic()
        try:
            result = subprocess.run(
                cmd,
                cwd=cwd,
                capture_output=True,
                text=True,
                timeout=timeout,
            )
        except FileNotFoundError as exc:
            raise BenchCommandError(f"Executable not found while running: {safe_cmd_str}") from exc
        except subprocess.TimeoutExpired as exc:
            logger.error("Bench command timed out after %ds: %s", timeout, safe_cmd_str)
            raise BenchCommandError(
                f"Command '{self._sanitize_args(bench_args)}' timed out after {timeout}s"
            ) from exc

        elapsed = time.monotonic() - start_time
        logger.debug("Command completed in %.2fs (exit code %d)", elapsed, result.returncode)

        if result.returncode != 0:
            error_details = result.stderr.strip() or result.stdout.strip()
            logger.error(
                "Bench command failed (Exit code %d): %s",
                result.returncode,
                error_details,
            )
            raise BenchCommandError(
                f"Command '{self._sanitize_args(bench_args)}' failed (exit {result.returncode}): {error_details}"
            )

        return result