#!/usr/bin/env python3
"""Frappe CRM Docker Container Monitoring & Auto-Recovery Tool.

Enterprise-grade monitoring script for Frappe CRM that provides:
1. Real-time monitoring of all Frappe CRM Docker containers.
2. Container status, health status, CPU and memory usage collection.
3. Identification of stopped or unhealthy containers.
4. Container log collection and error pattern analysis.
5. JSON-format system health report generation.
6. Optional auto-restart feature for stopped/unhealthy containers.
7. Comprehensive logging, sensitive data masking, and error handling.
8. Unified Command-Line Interface (CLI).

Author: Bulbul Das (@dasBulbul03)
Role: DevOps Engineering Intern
Organization: PearlThoughts
"""

from __future__ import annotations

import argparse
import json
import logging
import re
import shlex
import subprocess
import sys
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, ClassVar

# ---------------------------------------------------------------------------
# Constants & Defaults
# ---------------------------------------------------------------------------
DEFAULT_COMPOSE_PROJECT = "crm"
DEFAULT_LOG_FILE = Path("./automation/logs/frappe_monitor.log")
DEFAULT_REPORT_DIR = Path("./automation/reports")
DEFAULT_LOG_LINES = 100
DEFAULT_ERROR_PATTERNS = [
    r"(?i)(error|exception|traceback|critical|fatal|failed|panic|oom)",
    r"(?i)(connection refused|timeout|broken pipe)",
    r"(?i)(out of memory|killed process|segfault)",
]
# Containers that belong to this project (populated by auto-discovery)
KNOWN_CONTAINERS = ["crm-frappe-1", "crm-redis-1", "crm-mariadb-1"]


# ---------------------------------------------------------------------------
# Custom Exceptions
# ---------------------------------------------------------------------------
class MonitorError(Exception):
    """Base exception for Frappe CRM monitoring automation."""


class DockerCommandError(MonitorError):
    """Raised when a Docker CLI command fails unexpectedly."""


class ContainerNotFoundError(MonitorError):
    """Raised when a specified container does not exist."""


class AutoRecoveryError(MonitorError):
    """Raised when an auto-restart attempt fails."""


# ---------------------------------------------------------------------------
# Sensitive Data Filter & Logging Setup
# ---------------------------------------------------------------------------
class SensitiveDataFilter(logging.Filter):
    """Redacts sensitive credentials and tokens from log messages."""

    PATTERNS: ClassVar[list[tuple[re.Pattern, str]]] = [
        (re.compile(r"(MYSQL_ROOT_PASSWORD=)(\S+)", re.IGNORECASE), r"\1***"),
        (re.compile(r"(password[=:\s]+)(\S+)", re.IGNORECASE), r"\1***"),
        (re.compile(r"(token[=:\s]+)(\S+)", re.IGNORECASE), r"\1***"),
        (re.compile(r"(secret[=:\s]+)(\S+)", re.IGNORECASE), r"\1***"),
        (re.compile(r'("db_password":\s*")[^"]+(")', re.IGNORECASE), r"\1***\2"),
    ]

    def filter(self, record: logging.LogRecord) -> bool:
        if isinstance(record.msg, str):
            for pattern, repl in self.PATTERNS:
                record.msg = pattern.sub(repl, record.msg)
        return True


def setup_logging(log_file: Path | None = None, verbose: bool = False) -> logging.Logger:
    """Configures multi-channel logging (File & Console) with credential masking."""
    logger = logging.getLogger("frappe_monitor")
    logger.setLevel(logging.DEBUG if verbose else logging.INFO)
    logger.handlers.clear()

    sensitive_filter = SensitiveDataFilter()
    fmt = logging.Formatter(
        fmt="%(asctime)s [%(levelname)-8s] %(message)s",
        datefmt="%Y-%m-%dT%H:%M:%S",
    )

    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.DEBUG if verbose else logging.INFO)
    console_handler.setFormatter(fmt)
    console_handler.addFilter(sensitive_filter)
    logger.addHandler(console_handler)

    # File handler
    if log_file:
        try:
            log_file.parent.mkdir(parents=True, exist_ok=True)
            file_handler = logging.FileHandler(log_file, encoding="utf-8")
            file_handler.setLevel(logging.DEBUG)
            file_handler.setFormatter(fmt)
            file_handler.addFilter(sensitive_filter)
            logger.addHandler(file_handler)
        except OSError as exc:
            logger.warning("Could not open log file '%s': %s — file logging disabled.", log_file, exc)

    return logger


# ---------------------------------------------------------------------------
# Data Models
# ---------------------------------------------------------------------------
@dataclass
class ContainerStats:
    """CPU and memory usage parsed from `docker stats --no-stream`."""

    cpu_percent: float = 0.0
    mem_usage: str = "N/A"
    mem_percent: float = 0.0
    net_io: str = "N/A"
    block_io: str = "N/A"
    pids: int = 0


@dataclass
class LogAnalysis:
    """Results of scanning container logs for error patterns."""

    total_lines_scanned: int = 0
    error_lines_found: int = 0
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    scan_status: str = "NOT_SCANNED"


@dataclass
class ContainerReport:
    """Full health snapshot for a single container."""

    name: str
    container_id: str
    image: str
    status: str          # running / exited / paused / …
    health_status: str   # healthy / unhealthy / starting / none
    is_running: bool
    is_healthy: bool
    started_at: str
    finished_at: str
    restart_count: int
    exit_code: int
    stats: ContainerStats = field(default_factory=ContainerStats)
    log_analysis: LogAnalysis = field(default_factory=LogAnalysis)
    auto_restart_attempted: bool = False
    auto_restart_succeeded: bool = False
    alerts: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class SystemHealthReport:
    """Aggregated health report for the entire Frappe CRM stack."""

    report_id: str
    generated_at: str
    compose_project: str
    overall_status: str          # HEALTHY / DEGRADED / CRITICAL
    total_containers: int
    running_count: int
    stopped_count: int
    unhealthy_count: int
    containers: list[dict[str, Any]] = field(default_factory=list)
    summary: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


# ---------------------------------------------------------------------------
# Docker Helper
# ---------------------------------------------------------------------------
def _run(cmd: list[str], *, capture: bool = True, check: bool = True,
         timeout: int = 30) -> subprocess.CompletedProcess:
    """Run a command and return CompletedProcess. Raises DockerCommandError on failure."""
    try:
        return subprocess.run(
            cmd,
            capture_output=capture,
            text=True,
            check=check,
            timeout=timeout,
        )
    except subprocess.CalledProcessError as exc:
        raise DockerCommandError(
            f"Command {shlex.join(cmd)!r} failed (exit {exc.returncode}): {exc.stderr.strip()}"
        ) from exc
    except subprocess.TimeoutExpired as exc:
        raise DockerCommandError(
            f"Command {shlex.join(cmd)!r} timed out after {timeout}s."
        ) from exc
    except FileNotFoundError as exc:
        raise DockerCommandError(
            "Docker CLI not found. Ensure Docker is installed and in PATH."
        ) from exc


def _parse_percent(value: str) -> float:
    """Parse '3.92%' → 3.92, tolerates '--' or empty."""
    try:
        return float(value.rstrip("%"))
    except (ValueError, AttributeError):
        return 0.0


# ---------------------------------------------------------------------------
# Core Monitoring Engine
# ---------------------------------------------------------------------------
class FrappeMonitor:
    """Monitors all Frappe CRM containers and optionally auto-restarts unhealthy ones."""

    def __init__(
        self,
        compose_project: str = DEFAULT_COMPOSE_PROJECT,
        log_lines: int = DEFAULT_LOG_LINES,
        report_dir: Path = DEFAULT_REPORT_DIR,
        auto_restart: bool = False,
        logger: logging.Logger | None = None,
    ) -> None:
        self.compose_project = compose_project
        self.log_lines = log_lines
        self.report_dir = report_dir
        self.auto_restart = auto_restart
        self.log = logger or logging.getLogger("frappe_monitor")
        self._error_patterns: list[re.Pattern] = [
            re.compile(p) for p in DEFAULT_ERROR_PATTERNS
        ]

    # ------------------------------------------------------------------
    # Container Discovery
    # ------------------------------------------------------------------
    def discover_containers(self) -> list[str]:
        """Return names of all containers belonging to the compose project."""
        self.log.info("Discovering containers for project: '%s' ...", self.compose_project)
        result = _run(
            ["docker", "ps", "-a",
             "--filter", f"label=com.docker.compose.project={self.compose_project}",
             "--format", "{{.Names}}"],
            check=False,
        )
        names = [n.strip() for n in result.stdout.splitlines() if n.strip()]

        # Fallback: match by name prefix if label filter returns nothing
        if not names:
            self.log.debug(
                "Label-based discovery returned no containers — falling back to name prefix."
            )
            result = _run(
                ["docker", "ps", "-a",
                 "--filter", f"name={self.compose_project}-",
                 "--format", "{{.Names}}"],
                check=False,
            )
            names = [n.strip() for n in result.stdout.splitlines() if n.strip()]

        if not names:
            self.log.warning(
                "No containers found for project '%s'. Falling back to known container list.",
                self.compose_project,
            )
            names = KNOWN_CONTAINERS

        self.log.info("Discovered %d container(s): %s", len(names), ", ".join(names))
        return names

    # ------------------------------------------------------------------
    # Inspect
    # ------------------------------------------------------------------
    def _inspect_container(self, name: str) -> dict[str, Any]:
        """Return raw `docker inspect` data for one container."""
        result = _run(["docker", "inspect", name], check=False)
        if result.returncode != 0:
            raise ContainerNotFoundError(
                f"Container '{name}' not found or cannot be inspected."
            )
        data = json.loads(result.stdout)
        if not data:
            raise ContainerNotFoundError(f"Empty inspect output for '{name}'.")
        return data[0]

    def _build_container_report(self, name: str) -> ContainerReport:
        """Build a ContainerReport from docker inspect data."""
        self.log.debug("Inspecting container: %s", name)
        raw = self._inspect_container(name)

        state = raw.get("State", {})
        health_obj = state.get("Health", {})
        health_status = health_obj.get("Status", "none")

        is_running: bool = state.get("Running", False)
        is_healthy: bool = is_running and health_status in ("healthy", "none")

        return ContainerReport(
            name=name,
            container_id=raw.get("Id", "")[:12],
            image=raw.get("Config", {}).get("Image", "unknown"),
            status=state.get("Status", "unknown"),
            health_status=health_status,
            is_running=is_running,
            is_healthy=is_healthy,
            started_at=state.get("StartedAt", ""),
            finished_at=state.get("FinishedAt", ""),
            restart_count=raw.get("RestartCount", 0),
            exit_code=state.get("ExitCode", 0),
        )

    # ------------------------------------------------------------------
    # Stats
    # ------------------------------------------------------------------
    def _collect_stats(self, name: str) -> ContainerStats:
        """Collect real-time CPU / memory stats for a running container."""
        self.log.debug("Collecting stats for: %s", name)
        result = _run(
            ["docker", "stats", "--no-stream", "--format", "{{json .}}", name],
            check=False,
            timeout=15,
        )
        if result.returncode != 0 or not result.stdout.strip():
            self.log.warning("Could not collect stats for '%s' (container may be stopped).", name)
            return ContainerStats()

        try:
            raw = json.loads(result.stdout.strip().splitlines()[0])
        except (json.JSONDecodeError, IndexError):
            return ContainerStats()

        return ContainerStats(
            cpu_percent=_parse_percent(raw.get("CPUPerc", "0%")),
            mem_usage=raw.get("MemUsage", "N/A"),
            mem_percent=_parse_percent(raw.get("MemPerc", "0%")),
            net_io=raw.get("NetIO", "N/A"),
            block_io=raw.get("BlockIO", "N/A"),
            pids=int(raw.get("PIDs", 0)) if str(raw.get("PIDs", "0")).isdigit() else 0,
        )

    # ------------------------------------------------------------------
    # Log Analysis
    # ------------------------------------------------------------------
    def _analyze_logs(self, name: str) -> LogAnalysis:
        """Fetch recent container logs and scan for error/warning patterns."""
        self.log.debug("Fetching logs for: %s (last %d lines)", name, self.log_lines)
        result = _run(
            ["docker", "logs", "--tail", str(self.log_lines), name],
            check=False,
            timeout=20,
        )
        # docker logs writes to stderr by design
        raw_text = (result.stdout + result.stderr)
        lines = raw_text.splitlines()

        errors: list[str] = []
        warnings: list[str] = []

        warning_re = re.compile(r"(?i)\b(warn|warning|deprecated)\b")

        for line in lines:
            if any(p.search(line) for p in self._error_patterns):
                errors.append(line.strip())
            elif warning_re.search(line):
                warnings.append(line.strip())

        return LogAnalysis(
            total_lines_scanned=len(lines),
            error_lines_found=len(errors),
            errors=errors[:20],       # cap at 20 entries in report
            warnings=warnings[:10],   # cap at 10 entries
            scan_status="COMPLETED",
        )

    # ------------------------------------------------------------------
    # Alerts
    # ------------------------------------------------------------------
    def _generate_alerts(self, report: ContainerReport) -> list[str]:
        """Generate human-readable alert strings for a container."""
        alerts: list[str] = []

        if not report.is_running:
            alerts.append(
                f"CRITICAL: Container '{report.name}' is STOPPED "
                f"(exit_code={report.exit_code})."
            )
        if report.health_status == "unhealthy":
            alerts.append(f"WARNING: Container '{report.name}' health check is UNHEALTHY.")
        if report.health_status == "starting":
            alerts.append(f"INFO: Container '{report.name}' health check is STARTING.")
        if report.stats.cpu_percent > 90:
            alerts.append(
                f"WARNING: Container '{report.name}' CPU usage is HIGH "
                f"({report.stats.cpu_percent:.1f}%)."
            )
        if report.stats.mem_percent > 90:
            alerts.append(
                f"WARNING: Container '{report.name}' memory usage is HIGH "
                f"({report.stats.mem_percent:.1f}%)."
            )
        if report.restart_count > 5:
            alerts.append(
                f"WARNING: Container '{report.name}' has restarted "
                f"{report.restart_count} times — possible crash-loop."
            )
        if report.log_analysis.error_lines_found > 0:
            alerts.append(
                f"INFO: Container '{report.name}' has "
                f"{report.log_analysis.error_lines_found} error line(s) in recent logs."
            )
        return alerts

    # ------------------------------------------------------------------
    # Auto-Restart
    # ------------------------------------------------------------------
    def _attempt_auto_restart(self, report: ContainerReport) -> None:
        """Attempt to restart a stopped or unhealthy container."""
        self.log.warning(
            "Auto-restart triggered for container: '%s' (status=%s, health=%s).",
            report.name, report.status, report.health_status,
        )
        result = _run(
            ["docker", "restart", report.name],
            check=False,
            timeout=60,
        )
        report.auto_restart_attempted = True
        if result.returncode == 0:
            report.auto_restart_succeeded = True
            report.alerts.append(
                f"AUTO-RECOVERY: Container '{report.name}' was successfully restarted."
            )
            self.log.info("Auto-restart SUCCEEDED for '%s'.", report.name)
        else:
            report.auto_restart_succeeded = False
            err_msg = result.stderr.strip()
            report.alerts.append(
                f"AUTO-RECOVERY FAILED: Could not restart '{report.name}'. Error: {err_msg}"
            )
            self.log.error("Auto-restart FAILED for '%s': %s", report.name, err_msg)

    # ------------------------------------------------------------------
    # Main Monitor Loop
    # ------------------------------------------------------------------
    def monitor(self, container_names: list[str] | None = None) -> SystemHealthReport:
        """Run a full monitoring pass over all Frappe CRM containers."""
        ts = datetime.now(timezone.utc)
        report_id = ts.strftime("%Y%m%d_%H%M%S_monitor")
        generated_at = ts.isoformat()

        targets = container_names or self.discover_containers()

        container_reports: list[ContainerReport] = []
        stopped_count = 0
        unhealthy_count = 0

        for name in targets:
            self.log.info("── Monitoring container: %s", name)
            try:
                cr = self._build_container_report(name)
            except ContainerNotFoundError as exc:
                self.log.error("Skipping '%s': %s", name, exc)
                # Create a minimal report for the missing container
                cr = ContainerReport(
                    name=name,
                    container_id="N/A",
                    image="N/A",
                    status="not_found",
                    health_status="none",
                    is_running=False,
                    is_healthy=False,
                    started_at="",
                    finished_at="",
                    restart_count=0,
                    exit_code=-1,
                    alerts=[f"CRITICAL: Container '{name}' was NOT FOUND on this host."],
                )
                stopped_count += 1
                container_reports.append(cr)
                continue

            # Collect resource stats (only meaningful when running)
            if cr.is_running:
                cr.stats = self._collect_stats(name)

            # Analyze logs
            cr.log_analysis = self._analyze_logs(name)

            # Generate alerts
            cr.alerts = self._generate_alerts(cr)

            # Log individual status
            status_icon = "✓" if cr.is_running else "✗"
            self.log.info(
                "  [%s] %s | status=%-10s | health=%-10s | cpu=%-6s | mem=%s",
                status_icon, name, cr.status, cr.health_status,
                f"{cr.stats.cpu_percent:.1f}%", cr.stats.mem_usage,
            )
            if cr.alerts:
                for alert in cr.alerts:
                    self.log.warning("  ALERT: %s", alert)

            # Auto-restart logic
            needs_restart = (not cr.is_running) or (cr.health_status == "unhealthy")
            if self.auto_restart and needs_restart:
                self._attempt_auto_restart(cr)

            # Tally
            if not cr.is_running:
                stopped_count += 1
            if cr.health_status == "unhealthy":
                unhealthy_count += 1

            container_reports.append(cr)

        # Overall system status
        running_count = len(targets) - stopped_count
        if stopped_count == 0 and unhealthy_count == 0:
            overall_status = "HEALTHY"
        elif stopped_count >= len(targets):
            overall_status = "CRITICAL"
        elif stopped_count > 0 or unhealthy_count > 0:
            overall_status = "DEGRADED"
        else:
            overall_status = "HEALTHY"

        # Build summary
        summary = [
            f"Total containers monitored: {len(targets)}",
            f"Running: {running_count}  |  Stopped: {stopped_count}  |  Unhealthy: {unhealthy_count}",
            f"Overall system status: {overall_status}",
        ]
        if self.auto_restart:
            restarted = sum(1 for r in container_reports if r.auto_restart_succeeded)
            summary.append(f"Auto-restart attempts: {len([r for r in container_reports if r.auto_restart_attempted])}  |  Succeeded: {restarted}")

        health_report = SystemHealthReport(
            report_id=report_id,
            generated_at=generated_at,
            compose_project=self.compose_project,
            overall_status=overall_status,
            total_containers=len(targets),
            running_count=running_count,
            stopped_count=stopped_count,
            unhealthy_count=unhealthy_count,
            containers=[cr.to_dict() for cr in container_reports],
            summary=summary,
        )
        return health_report

    # ------------------------------------------------------------------
    # Report Saving
    # ------------------------------------------------------------------
    def save_report(self, report: SystemHealthReport, report_id: str | None = None) -> Path:
        """Persist a SystemHealthReport as JSON to the reports directory."""
        self.report_dir.mkdir(parents=True, exist_ok=True)
        filename = f"{report_id or report.report_id}.json"
        output_path = self.report_dir / filename
        output_path.write_text(
            json.dumps(report.to_dict(), indent=2, default=str),
            encoding="utf-8",
        )
        self.log.info("Health report saved → %s", output_path)
        return output_path


# ---------------------------------------------------------------------------
# CLI Subcommand Implementations
# ---------------------------------------------------------------------------
def cmd_monitor(args: argparse.Namespace, monitor: FrappeMonitor) -> int:
    """Run a full monitoring pass and optionally print/save the report."""
    logger = logging.getLogger("frappe_monitor")
    logger.info("=" * 60)
    logger.info("  Frappe CRM Docker Monitoring Tool")
    logger.info("  Mode: %s", "AUTO-RESTART ENABLED" if args.auto_restart else "READ-ONLY")
    logger.info("=" * 60)

    report = monitor.monitor()

    logger.info("─" * 60)
    for line in report.summary:
        logger.info("  %s", line)
    logger.info("─" * 60)

    if args.save_report or not args.no_report:
        path = monitor.save_report(report)
        logger.info("Report written to: %s", path)

    if args.print_json:
        print(json.dumps(report.to_dict(), indent=2, default=str))

    # Exit code reflects overall status
    return 0 if report.overall_status == "HEALTHY" else 1


def cmd_status(args: argparse.Namespace, monitor: FrappeMonitor) -> int:
    """Print a quick summary table of all container statuses."""
    logger = logging.getLogger("frappe_monitor")
    names = monitor.discover_containers()

    logger.info("─" * 70)
    logger.info("  %-25s %-12s %-12s %-10s %-10s", "CONTAINER", "STATUS", "HEALTH", "CPU%", "MEM%")
    logger.info("─" * 70)

    exit_code = 0
    for name in names:
        try:
            cr = monitor._build_container_report(name)
            if cr.is_running:
                stats = monitor._collect_stats(name)
                cr.stats = stats
            status_icon = "✓" if cr.is_running else "✗"
            logger.info(
                "  [%s] %-23s %-12s %-12s %-10s %-10s",
                status_icon, name, cr.status, cr.health_status,
                f"{cr.stats.cpu_percent:.1f}%", f"{cr.stats.mem_percent:.1f}%",
            )
            if not cr.is_running:
                exit_code = 1
        except (ContainerNotFoundError, DockerCommandError) as exc:
            logger.error("  [✗] %-23s ERROR: %s", name, exc)
            exit_code = 1

    logger.info("─" * 70)
    return exit_code


def cmd_logs(args: argparse.Namespace, monitor: FrappeMonitor) -> int:
    """Analyze logs of all or a specific container and report errors."""
    logger = logging.getLogger("frappe_monitor")
    names = [args.container] if args.container else monitor.discover_containers()

    exit_code = 0
    for name in names:
        logger.info("Analyzing logs for: %s (last %d lines)", name, monitor.log_lines)
        try:
            analysis = monitor._analyze_logs(name)
        except DockerCommandError as exc:
            logger.error("Log fetch failed for '%s': %s", name, exc)
            exit_code = 1
            continue

        logger.info(
            "  Lines scanned: %d  |  Errors found: %d  |  Warnings: %d",
            analysis.total_lines_scanned, analysis.error_lines_found, len(analysis.warnings),
        )
        if analysis.errors:
            logger.warning("  Top error lines:")
            for err in analysis.errors[:10]:
                logger.warning("    → %s", err[:200])
        if analysis.error_lines_found > 0:
            exit_code = 1

    return exit_code


def cmd_restart(args: argparse.Namespace, monitor: FrappeMonitor) -> int:
    """Manually restart a specific container (or all stopped containers)."""
    logger = logging.getLogger("frappe_monitor")

    if args.container:
        targets = [args.container]
    else:
        # Find all stopped containers
        all_names = monitor.discover_containers()
        targets = []
        for name in all_names:
            try:
                cr = monitor._build_container_report(name)
                if not cr.is_running or cr.health_status == "unhealthy":
                    targets.append(name)
            except (ContainerNotFoundError, DockerCommandError):
                pass

    if not targets:
        logger.info("No stopped or unhealthy containers found — nothing to restart.")
        return 0

    exit_code = 0
    for name in targets:
        logger.info("Restarting container: %s ...", name)
        result = _run(["docker", "restart", name], check=False, timeout=60)
        if result.returncode == 0:
            logger.info("  SUCCESS: '%s' restarted.", name)
        else:
            logger.error("  FAILED to restart '%s': %s", name, result.stderr.strip())
            exit_code = 1

    return exit_code


def cmd_report(args: argparse.Namespace, monitor: FrappeMonitor) -> int:
    """Generate and save a full JSON health report."""
    logger = logging.getLogger("frappe_monitor")
    report = monitor.monitor()
    path = monitor.save_report(report)
    logger.info("Full health report generated: %s", path)
    if args.print_json:
        print(json.dumps(report.to_dict(), indent=2, default=str))
    return 0 if report.overall_status == "HEALTHY" else 1


# ---------------------------------------------------------------------------
# CLI Definition
# ---------------------------------------------------------------------------
def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="monitor.py",
        description=(
            "Frappe CRM Docker Container Monitoring & Auto-Recovery Tool.\n"
            "Monitors container health, resources, logs, and optionally auto-restarts unhealthy containers."
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python3 automation/monitor.py monitor                    # Full monitoring pass (read-only)
  python3 automation/monitor.py monitor --auto-restart     # Monitor + auto-restart stopped containers
  python3 automation/monitor.py status                     # Quick status table
  python3 automation/monitor.py logs                       # Analyze logs for all containers
  python3 automation/monitor.py logs --container crm-frappe-1  # Logs for one container
  python3 automation/monitor.py restart                    # Restart all stopped/unhealthy containers
  python3 automation/monitor.py restart --container crm-redis-1  # Restart specific container
  python3 automation/monitor.py report --print-json        # Generate JSON report and print to stdout
        """,
    )

    # Global options
    parser.add_argument(
        "--project", default=DEFAULT_COMPOSE_PROJECT,
        help=f"Docker Compose project name (default: {DEFAULT_COMPOSE_PROJECT})",
    )
    parser.add_argument(
        "--log-file", type=Path, default=DEFAULT_LOG_FILE,
        help=f"Path to log file (default: {DEFAULT_LOG_FILE})",
    )
    parser.add_argument(
        "--report-dir", type=Path, default=DEFAULT_REPORT_DIR,
        help=f"Directory for JSON health reports (default: {DEFAULT_REPORT_DIR})",
    )
    parser.add_argument(
        "--log-lines", type=int, default=DEFAULT_LOG_LINES,
        help=f"Number of recent log lines to analyze per container (default: {DEFAULT_LOG_LINES})",
    )
    parser.add_argument(
        "--verbose", "-v", action="store_true",
        help="Enable debug-level logging.",
    )

    subparsers = parser.add_subparsers(dest="command", required=True)

    # --- monitor ---
    p_monitor = subparsers.add_parser(
        "monitor",
        help="Run a full monitoring pass: status, stats, logs, alerts.",
    )
    p_monitor.add_argument(
        "--auto-restart", action="store_true",
        help="Automatically restart any stopped or unhealthy container found.",
    )
    p_monitor.add_argument(
        "--print-json", action="store_true",
        help="Print the JSON health report to stdout.",
    )
    p_monitor.add_argument(
        "--save-report", action="store_true", default=False,
        help="Explicitly save the JSON report to --report-dir.",
    )
    p_monitor.add_argument(
        "--no-report", action="store_true", default=False,
        help="Do NOT save the JSON report (overrides default save behaviour).",
    )

    # --- status ---
    subparsers.add_parser(
        "status",
        help="Print a quick status/stats table for all containers.",
    )

    # --- logs ---
    p_logs = subparsers.add_parser(
        "logs",
        help="Analyze container logs for errors and warnings.",
    )
    p_logs.add_argument(
        "--container", default=None,
        help="Analyze logs for this specific container only.",
    )

    # --- restart ---
    p_restart = subparsers.add_parser(
        "restart",
        help="Restart stopped/unhealthy containers (or a specific container).",
    )
    p_restart.add_argument(
        "--container", default=None,
        help="Name of a specific container to restart.",
    )

    # --- report ---
    p_report = subparsers.add_parser(
        "report",
        help="Generate and save a full JSON health report.",
    )
    p_report.add_argument(
        "--print-json", action="store_true",
        help="Also print the JSON report to stdout.",
    )

    return parser


# ---------------------------------------------------------------------------
# Entry Point
# ---------------------------------------------------------------------------
def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    logger = setup_logging(
        log_file=args.log_file,
        verbose=args.verbose,
    )

    auto_restart = getattr(args, "auto_restart", False)

    monitor = FrappeMonitor(
        compose_project=args.project,
        log_lines=args.log_lines,
        report_dir=args.report_dir,
        auto_restart=auto_restart,
        logger=logger,
    )

    command_map = {
        "monitor": cmd_monitor,
        "status": cmd_status,
        "logs": cmd_logs,
        "restart": cmd_restart,
        "report": cmd_report,
    }

    handler = command_map.get(args.command)
    if handler is None:
        parser.print_help()
        return 1

    try:
        return handler(args, monitor)
    except KeyboardInterrupt:
        logger.info("Interrupted by user.")
        return 130
    except MonitorError as exc:
        logger.critical("Fatal monitoring error: %s", exc)
        return 2
    except Exception as exc:  # noqa: BLE001
        logger.critical("Unexpected error: %s", exc, exc_info=args.verbose)
        return 3


if __name__ == "__main__":
    sys.exit(main())
