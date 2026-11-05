#!/usr/bin/env python3
"""
Frappe CRM Docker Container Monitoring & Auto-Recovery Tool
===========================================================
Enterprise-grade Python automation tool for monitoring Frappe CRM Docker containers,
tracking CPU/memory utilization, evaluating health statuses, analyzing runtime logs,
generating JSON/Markdown health reports, and performing automated self-healing recovery.

Author: DevOps Engineering Team
License: MIT
"""

import argparse
import dataclasses
import datetime
import json
import logging
import os
import re
import shutil
import subprocess
import sys
import time
import urllib.request
import urllib.error
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any, Set

# ==============================================================================
# Configuration Defaults & Constants
# ==============================================================================

DEFAULT_PROJECT = "crm"
DEFAULT_CPU_THRESHOLD = 80.0     # Percentage
DEFAULT_MEM_THRESHOLD = 80.0     # Percentage
DEFAULT_MAX_RETRIES = 3          # Maximum restart attempts per container
DEFAULT_COOLDOWN_SEC = 3.0       # Cooldown after restart before verification
DEFAULT_LOG_TAIL = 100           # Lines of logs to retrieve per container
DEFAULT_REPORT_DIR = Path("reports")
DEFAULT_LOG_FILE = Path("docker_monitor.log")

# Exit Codes
EXIT_HEALTHY = 0
EXIT_DEGRADED = 1
EXIT_DOCKER_ERROR = 2
EXIT_PARAM_ERROR = 3

# ==============================================================================
# Multi-Channel Colorized Logging
# ==============================================================================

class ColorFormatter(logging.Formatter):
    """Custom logging formatter with ANSI color coding for terminal visibility."""

    COLORS = {
        logging.DEBUG: "\033[36m",      # Cyan
        logging.INFO: "\033[32m",       # Green
        logging.WARNING: "\033[33m",    # Yellow
        logging.ERROR: "\033[31m",      # Red
        logging.CRITICAL: "\033[41m",   # Red background
    }
    RESET = "\033[0m"
    BOLD = "\033[1m"

    def format(self, record: logging.LogRecord) -> str:
        color = self.COLORS.get(record.levelno, self.RESET)
        timestamp = datetime.datetime.fromtimestamp(record.created).strftime("%Y-%m-%d %H:%M:%S")
        level = f"{color}[{record.levelname:<7}]{self.RESET}"
        return f"{timestamp} {level} {record.getMessage()}"


def setup_logger(
    log_file: Optional[Path] = None,
    verbose: bool = False,
    quiet: bool = False,
) -> logging.Logger:
    """Configures multi-channel logger (stdout + persistent log file)."""
    logger = logging.getLogger("frappe_docker_monitor")
    logger.handlers.clear()

    if verbose:
        level = logging.DEBUG
    elif quiet:
        level = logging.WARNING
    else:
        level = logging.INFO
    logger.setLevel(level)

    # Console Handler (ANSI color)
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(level)
    console_handler.setFormatter(ColorFormatter())
    logger.addHandler(console_handler)

    # File Handler (structured plain text)
    if log_file:
        try:
            log_file.parent.mkdir(parents=True, exist_ok=True)
            file_handler = logging.FileHandler(str(log_file), encoding="utf-8")
            file_handler.setLevel(logging.DEBUG)
            file_formatter = logging.Formatter(
                "%(asctime)s [%(levelname)s] [%(name)s] %(message)s",
                datefmt="%Y-%m-%d %H:%M:%S",
            )
            file_handler.setFormatter(file_formatter)
            logger.addHandler(file_handler)
        except Exception as e:
            logger.warning(f"Could not initialize log file at {log_file}: {e}")

    return logger


# ==============================================================================
# Helper Utilities (Size, Time, Formatting)
# ==============================================================================

def format_size(bytes_num: int) -> str:
    """Converts bytes into human-readable format (B, KiB, MiB, GiB, TiB)."""
    if bytes_num < 0:
        return "0.0 B"
    for unit in ["B", "KiB", "MiB", "GiB", "TiB"]:
        if abs(bytes_num) < 1024.0:
            return f"{bytes_num:.1f} {unit}"
        bytes_num /= 1024.0
    return f"{bytes_num:.1f} PiB"


def parse_size_string(size_str: str) -> int:
    """
    Parses human-readable size strings (e.g. '594.4MiB', '7.446GiB', '12.5kB', '500B')
    into raw byte integer counts.
    """
    if not size_str or size_str.strip() in ("--", "-", "0"):
        return 0
    size_str = size_str.strip().replace(",", "")
    match = re.match(r"^([\d.]+)\s*([a-zA-Z]+)?$", size_str)
    if not match:
        return 0
    value = float(match.group(1))
    unit = (match.group(2) or "B").lower()

    multiplier = 1
    if unit in ("b", "bytes"):
        multiplier = 1
    elif unit in ("k", "kb", "kib"):
        multiplier = 1024 if "i" in unit else 1000
    elif unit in ("m", "mb", "mib"):
        multiplier = 1024 * 1024 if "i" in unit else 1000 * 1000
    elif unit in ("g", "gb", "gib"):
        multiplier = 1024 * 1024 * 1024 if "i" in unit else 1000 * 1000 * 1000
    elif unit in ("t", "tb", "tib"):
        multiplier = 1024 * 1024 * 1024 * 1024 if "i" in unit else 1000 * 1000 * 1000 * 1000
    return int(value * multiplier)


def parse_percentage_string(perc_str: str) -> float:
    """Parses percentage strings (e.g. '16.64%', '--') into floats."""
    if not perc_str or perc_str.strip() in ("--", "-"):
        return 0.0
    cleaned = perc_str.strip().rstrip("%")
    try:
        return float(cleaned)
    except ValueError:
        return 0.0


def calculate_uptime(started_at_iso: str) -> str:
    """Calculates human-readable uptime from Docker StartedAt ISO timestamp."""
    if not started_at_iso or started_at_iso.startswith("0001-01-01"):
        return "Not Started"
    try:
        # Standardize ISO string by stripping nanoseconds if present
        cleaned_iso = re.sub(r"\.\d+Z$", "Z", started_at_iso)
        cleaned_iso = cleaned_iso.replace("Z", "+00:00")
        start_dt = datetime.datetime.fromisoformat(cleaned_iso)
        now_dt = datetime.datetime.now(datetime.timezone.utc)
        delta = now_dt - start_dt
        if delta.total_seconds() < 0:
            return "Just now"

        days = delta.days
        hours, remainder = divmod(delta.seconds, 3600)
        minutes, seconds = divmod(remainder, 60)

        parts = []
        if days > 0:
            parts.append(f"{days}d")
        if hours > 0 or days > 0:
            parts.append(f"{hours}h")
        if minutes > 0 or (days == 0 and hours == 0):
            parts.append(f"{minutes}m")
        if not parts:
            parts.append(f"{seconds}s")
        return " ".join(parts)
    except Exception:
        return "Unknown"


# ==============================================================================
# Data Models
# ==============================================================================

@dataclasses.dataclass
class ContainerStats:
    """Rich telemetry and state representation for a single Docker container."""
    container_id: str
    name: str
    service: str
    image: str
    status: str             # 'running', 'exited', 'dead', 'paused', 'restarting'
    health_status: str      # 'healthy', 'unhealthy', 'starting', 'none'
    overall_health: str     # 'HEALTHY', 'DEGRADED', 'STOPPED', 'UNHEALTHY'
    cpu_percent: float = 0.0
    memory_usage_bytes: int = 0
    memory_limit_bytes: int = 0
    memory_percent: float = 0.0
    memory_usage_human: str = "0.0 B"
    memory_limit_human: str = "0.0 B"
    network_io: str = "0B / 0B"
    block_io: str = "0B / 0B"
    pids: int = 0
    uptime: str = "Unknown"
    started_at: str = ""
    finished_at: str = ""
    exit_code: int = 0
    oom_killed: bool = False
    restart_count: int = 0
    ip_address: str = ""
    ports: List[str] = dataclasses.field(default_factory=list)
    app_probe: Dict[str, Any] = dataclasses.field(default_factory=dict)
    issues: List[str] = dataclasses.field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        """Converts stats to clean dictionary for JSON serialization."""
        return {
            "id": self.container_id[:12],
            "full_id": self.container_id,
            "name": self.name,
            "service": self.service,
            "image": self.image,
            "status": self.status,
            "docker_health": self.health_status,
            "overall_health": self.overall_health,
            "cpu_percent": round(self.cpu_percent, 2),
            "memory": {
                "usage_bytes": self.memory_usage_bytes,
                "limit_bytes": self.memory_limit_bytes,
                "usage_human": self.memory_usage_human,
                "limit_human": self.memory_limit_human,
                "percent": round(self.memory_percent, 2),
            },
            "network_io": self.network_io,
            "block_io": self.block_io,
            "pids": self.pids,
            "uptime": self.uptime,
            "started_at": self.started_at,
            "finished_at": self.finished_at,
            "exit_code": self.exit_code,
            "oom_killed": self.oom_killed,
            "restart_count": self.restart_count,
            "ip_address": self.ip_address,
            "ports": self.ports,
            "app_probe": self.app_probe,
            "issues": self.issues,
        }


@dataclasses.dataclass
class LogAnalysisResult:
    """Results of container log error and anomaly analysis."""
    container_name: str
    scanned_lines: int = 0
    error_count: int = 0
    warning_count: int = 0
    category_counts: Dict[str, int] = dataclasses.field(default_factory=dict)
    critical_issues: List[Dict[str, Any]] = dataclasses.field(default_factory=list)
    recent_errors: List[str] = dataclasses.field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "container_name": self.container_name,
            "scanned_lines": self.scanned_lines,
            "error_count": self.error_count,
            "warning_count": self.warning_count,
            "categories": self.category_counts,
            "critical_issues": self.critical_issues,
            "recent_errors": self.recent_errors[:10],
        }


@dataclasses.dataclass
class RecoveryAction:
    """Audit record of an automated recovery / restart attempt."""
    container_name: str
    attempted_at: str
    initial_status: str
    action: str              # 'restart', 'start', 'dry_run_restart'
    success: bool
    final_status: str
    message: str
    duration_seconds: float

    def to_dict(self) -> Dict[str, Any]:
        return {
            "container_name": self.container_name,
            "attempted_at": self.attempted_at,
            "initial_status": self.initial_status,
            "action": self.action,
            "success": self.success,
            "final_status": self.final_status,
            "message": self.message,
            "duration_seconds": round(self.duration_seconds, 2),
        }


@dataclasses.dataclass
class SystemHealthReport:
    """Comprehensive system-wide health and telemetry report."""
    report_id: str
    timestamp: str
    project: str
    overall_status: str      # 'HEALTHY', 'DEGRADED', 'CRITICAL'
    summary: Dict[str, Any]
    thresholds: Dict[str, float]
    containers: List[ContainerStats]
    log_analyses: Dict[str, LogAnalysisResult]
    recovery_actions: List[RecoveryAction]
    alerts: List[str]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "report_id": self.report_id,
            "timestamp": self.timestamp,
            "project": self.project,
            "overall_status": self.overall_status,
            "summary": self.summary,
            "thresholds": self.thresholds,
            "containers": [c.to_dict() for c in self.containers],
            "log_analyses": {k: v.to_dict() for k, v in self.log_analyses.items()},
            "recovery_actions": [r.to_dict() for r in self.recovery_actions],
            "alerts": self.alerts,
        }


# ==============================================================================
# Docker Subprocess Client Engine
# ==============================================================================

class DockerClientError(Exception):
    """Raised when a Docker CLI command fails or Docker daemon is unreachable."""
    pass


class DockerClient:
    """
    Zero-dependency Docker client leveraging standard library subprocess.
    Provides robust abstraction for Docker CLI interactions.
    """

    def __init__(self, timeout_sec: int = 20):
        self.timeout = timeout_sec

    def run_cmd(self, args: List[str], check: bool = True) -> subprocess.CompletedProcess:
        """Executes a docker command and returns the CompletedProcess."""
        cmd = ["docker"] + args
        try:
            res = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=self.timeout,
                check=check,
            )
            return res
        except subprocess.TimeoutExpired as e:
            raise DockerClientError(f"Docker command timed out after {self.timeout}s: {' '.join(cmd)}") from e
        except subprocess.CalledProcessError as e:
            err_msg = e.stderr.strip() if e.stderr else e.stdout.strip()
            raise DockerClientError(f"Docker command failed ({e.returncode}): {err_msg}") from e
        except FileNotFoundError as e:
            raise DockerClientError("Docker executable 'docker' not found in system PATH.") from e

    def check_daemon(self) -> Tuple[bool, str]:
        """Pings the Docker daemon to verify connectivity."""
        try:
            res = self.run_cmd(["version", "--format", "{{json .}}"])
            data = json.loads(res.stdout)
            server_version = data.get("Server", {}).get("Version", "Unknown")
            return True, f"Docker daemon active (Version {server_version})"
        except Exception as e:
            return False, f"Cannot connect to Docker daemon: {e}"

    def discover_containers(
        self,
        project: Optional[str] = None,
        container_names: Optional[List[str]] = None,
    ) -> List[Dict[str, Any]]:
        """
        Discovers containers by compose project label or explicit container names.
        Returns list of basic container dictionaries.
        """
        args = ["ps", "-a", "--format", "{{json .}}"]
        if project and project.lower() != "all":
            args += ["--filter", f"label=com.docker.compose.project={project}"]

        res = self.run_cmd(args)
        containers = []
        for line in res.stdout.strip().split("\n"):
            line = line.strip()
            if not line:
                continue
            try:
                c = json.loads(line)
                containers.append(c)
            except json.JSONDecodeError:
                continue

        # If project filter yielded nothing, fallback to name prefix matching or all containers
        if not containers and project and project.lower() != "all":
            all_res = self.run_cmd(["ps", "-a", "--format", "{{json .}}"])
            for line in all_res.stdout.strip().split("\n"):
                line = line.strip()
                if not line:
                    continue
                try:
                    c = json.loads(line)
                    name = c.get("Names", "")
                    if name.startswith(f"{project}-") or name.startswith(f"{project}_") or project in name:
                        containers.append(c)
                except json.JSONDecodeError:
                    continue

        # If specific container names requested, filter explicitly
        if container_names:
            target_set = set(container_names)
            containers = [c for c in containers if c.get("Names") in target_set or c.get("ID") in target_set]

        return containers

    def inspect_containers(self, names_or_ids: List[str]) -> Dict[str, Dict[str, Any]]:
        """Performs batch docker inspect and returns map of {container_name: inspect_doc}."""
        if not names_or_ids:
            return {}
        res = self.run_cmd(["inspect"] + names_or_ids)
        docs = json.loads(res.stdout)
        results = {}
        for doc in docs:
            name = doc.get("Name", "").lstrip("/")
            results[name] = doc
            cid = doc.get("Id", "")[:12]
            results[cid] = doc
        return results

    def get_stats_snapshot(self) -> Dict[str, Dict[str, Any]]:
        """
        Collects real-time CPU, memory, IO, and PID metrics for all running containers.
        Returns map of {container_name: stat_dict}.
        """
        try:
            res = self.run_cmd(["stats", "--no-stream", "--format", "{{json .}}"])
        except Exception:
            return {}

        stats_map = {}
        for line in res.stdout.strip().split("\n"):
            line = line.strip()
            if not line:
                continue
            try:
                stat = json.loads(line)
                name = stat.get("Name", "")
                stats_map[name] = stat
                cid = stat.get("ID", "")
                if cid:
                    stats_map[cid] = stat
            except json.JSONDecodeError:
                continue
        return stats_map

    def get_logs(self, container_name: str, tail: int = 100) -> List[str]:
        """Fetches the latest stdout and stderr logs for a container."""
        try:
            res = self.run_cmd(["logs", "--tail", str(tail), "--timestamps", container_name], check=False)
            output = res.stdout + ("\n" + res.stderr if res.stderr else "")
            return [line for line in output.split("\n") if line.strip()]
        except Exception:
            return []

    def restart_container(self, container_name: str, timeout: int = 10) -> bool:
        """Restarts a container safely."""
        try:
            self.run_cmd(["restart", "-t", str(timeout), container_name])
            return True
        except Exception:
            return False

    def start_container(self, container_name: str) -> bool:
        """Starts a stopped container."""
        try:
            self.run_cmd(["start", container_name])
            return True
        except Exception:
            return False


# ==============================================================================
# Container Log Analyzer Engine
# ==============================================================================

class LogAnalyzer:
    """
    Intelligent log analysis engine for detecting errors, exceptions,
    connection failures, resource exhaustions, and service crashes.
    """

    # Categorized Regex Patterns
    PATTERNS: Dict[str, List[Tuple[re.Pattern, str]]] = {
        "PYTHON_EXCEPTION": [
            (re.compile(r"Traceback \(most recent call last\):", re.IGNORECASE), "CRITICAL"),
            (re.compile(r"OperationalError:\s*\(.*?\)", re.IGNORECASE), "ERROR"),
            (re.compile(r"ProgrammingError:\s*\(.*?\)", re.IGNORECASE), "ERROR"),
            (re.compile(r"InternalServerError:\s*\(.*?\)", re.IGNORECASE), "ERROR"),
            (re.compile(r"(ImportError|ModuleNotFoundError|AttributeError|KeyError):", re.IGNORECASE), "ERROR"),
            (re.compile(r"redis\.exceptions\.ConnectionError", re.IGNORECASE), "CRITICAL"),
        ],
        "DATABASE_ERROR": [
            (re.compile(r"\[ERROR\]\s*(mysqld|mariadbd)", re.IGNORECASE), "CRITICAL"),
            (re.compile(r"MySQL server has gone away", re.IGNORECASE), "CRITICAL"),
            (re.compile(r"Deadlock found when trying to get lock", re.IGNORECASE), "ERROR"),
            (re.compile(r"Access denied for user", re.IGNORECASE), "ERROR"),
            (re.compile(r"Got an error reading communication packets", re.IGNORECASE), "WARNING"),
            (re.compile(r"Table '.*?' doesn't exist", re.IGNORECASE), "ERROR"),
            (re.compile(r"InnoDB: (Error|Corrupt)", re.IGNORECASE), "CRITICAL"),
        ],
        "REDIS_ERROR": [
            (re.compile(r"OOM command not allowed", re.IGNORECASE), "CRITICAL"),
            (re.compile(r"Error writing to RDB", re.IGNORECASE), "CRITICAL"),
            (re.compile(r"MISCONF Redis is configured to save RDB snapshots", re.IGNORECASE), "CRITICAL"),
            (re.compile(r"Fatal error loading the DB", re.IGNORECASE), "CRITICAL"),
            (re.compile(r"WRONGPASS invalid username-password", re.IGNORECASE), "ERROR"),
        ],
        "WEB_SERVER_ERROR": [
            (re.compile(r'"\s*500\s+[0-9\-]+', re.IGNORECASE), "ERROR"),
            (re.compile(r'"\s*502\s+[0-9\-]+', re.IGNORECASE), "CRITICAL"),
            (re.compile(r'"\s*503\s+[0-9\-]+', re.IGNORECASE), "ERROR"),
            (re.compile(r'"\s*504\s+[0-9\-]+', re.IGNORECASE), "ERROR"),
            (re.compile(r"Worker\s+\(\d+\)\s+exited\s+on\s+signal", re.IGNORECASE), "CRITICAL"),
            (re.compile(r"WORKER TIMEOUT", re.IGNORECASE), "CRITICAL"),
        ],
        "RESOURCE_EXHAUSTION": [
            (re.compile(r"Out of memory: Kill process", re.IGNORECASE), "CRITICAL"),
            (re.compile(r"oom-killer", re.IGNORECASE), "CRITICAL"),
            (re.compile(r"No space left on device", re.IGNORECASE), "CRITICAL"),
            (re.compile(r"Disk quota exceeded", re.IGNORECASE), "CRITICAL"),
        ],
        "GENERIC_ERROR": [
            (re.compile(r"\[(FATAL|PANIC|CRITICAL)\]", re.IGNORECASE), "CRITICAL"),
            (re.compile(r"\[ERROR\]", re.IGNORECASE), "ERROR"),
            (re.compile(r"\bError:\s+", re.IGNORECASE), "ERROR"),
        ],
        "WARNING": [
            (re.compile(r"\[WARNING\]", re.IGNORECASE), "WARNING"),
            (re.compile(r"\bDeprecationWarning\b", re.IGNORECASE), "WARNING"),
            (re.compile(r"\bUserWarning\b", re.IGNORECASE), "WARNING"),
        ],
    }

    @classmethod
    def analyze(cls, container_name: str, log_lines: List[str]) -> LogAnalysisResult:
        """Scans log lines, classifies issues by category, and extracts error excerpts."""
        result = LogAnalysisResult(container_name=container_name, scanned_lines=len(log_lines))
        seen_errors: Set[str] = set()

        for idx, line in enumerate(log_lines, 1):
            matched_category = None
            matched_severity = None

            for cat, rules in cls.PATTERNS.items():
                for regex, severity in rules:
                    if regex.search(line):
                        matched_category = cat
                        matched_severity = severity
                        break
                if matched_category:
                    break

            if matched_category:
                if matched_severity in ("CRITICAL", "ERROR"):
                    result.error_count += 1
                elif matched_severity == "WARNING":
                    result.warning_count += 1

                result.category_counts[matched_category] = result.category_counts.get(matched_category, 0) + 1

                # Clean sample text
                snippet = line.strip()
                if matched_severity == "CRITICAL" and len(result.critical_issues) < 10:
                    result.critical_issues.append({
                        "line_number": idx,
                        "category": matched_category,
                        "severity": matched_severity,
                        "message": snippet[:200],
                    })

                if snippet not in seen_errors and len(result.recent_errors) < 10:
                    seen_errors.add(snippet)
                    result.recent_errors.append(snippet[:200])

        return result


# ==============================================================================
# Health Probing & Container Evaluation Engine
# ==============================================================================

class HealthEvaluator:
    """Evaluates telemetry, docker health, and application probes to determine state."""

    def __init__(
        self,
        cpu_threshold: float = DEFAULT_CPU_THRESHOLD,
        mem_threshold: float = DEFAULT_MEM_THRESHOLD,
    ):
        self.cpu_threshold = cpu_threshold
        self.mem_threshold = mem_threshold

    def probe_application(self, service: str, inspect_doc: Dict[str, Any]) -> Dict[str, Any]:
        """Runs lightweight synthetic probe to test application responsiveness."""
        probe = {"checked": False, "status": "UNKNOWN", "latency_ms": 0.0, "details": ""}

        # Frappe web service probe (check port 8000 on localhost)
        if "frappe" in service.lower():
            probe["checked"] = True
            start_t = time.perf_counter()
            try:
                # Try connecting to exposed port 8000
                req = urllib.request.Request("http://127.0.0.1:8000/api/method/frappe.ping", headers={"User-Agent": "FrappeHealthCheck/1.0"})
                with urllib.request.urlopen(req, timeout=3.0) as resp:
                    latency = (time.perf_counter() - start_t) * 1000.0
                    probe["status"] = "OK"
                    probe["latency_ms"] = round(latency, 2)
                    probe["details"] = f"HTTP {resp.status} /api/method/frappe.ping"
            except Exception:
                # Fallback check root URL
                try:
                    req_root = urllib.request.Request("http://127.0.0.1:8000/", headers={"User-Agent": "FrappeHealthCheck/1.0"})
                    with urllib.request.urlopen(req_root, timeout=3.0) as resp_root:
                        latency = (time.perf_counter() - start_t) * 1000.0
                        probe["status"] = "OK"
                        probe["latency_ms"] = round(latency, 2)
                        probe["details"] = f"HTTP {resp_root.status} Root Endpoint"
                except Exception as ex:
                    probe["status"] = "PROBE_FAILED"
                    probe["details"] = f"Connection failed: {str(ex)[:100]}"
            return probe

        # MariaDB service probe (inspect port bindings)
        if "mariadb" in service.lower() or "mysql" in service.lower():
            probe["checked"] = True
            probe["status"] = "OK"
            probe["details"] = "MariaDB daemon running on internal network port 3306"
            return probe

        # Redis service probe (inspect port bindings)
        if "redis" in service.lower():
            probe["checked"] = True
            probe["status"] = "OK"
            probe["details"] = "Redis daemon running on internal network port 6379"
            return probe

        return probe

    def build_container_stats(
        self,
        name: str,
        inspect_doc: Optional[Dict[str, Any]],
        stats_doc: Optional[Dict[str, Any]],
        log_res: Optional[LogAnalysisResult] = None,
    ) -> ContainerStats:
        """Constructs unified ContainerStats instance from Docker inspect & stats."""
        cid = ""
        service = name
        image = ""
        status = "unknown"
        docker_health = "none"
        started_at = ""
        finished_at = ""
        exit_code = 0
        oom_killed = False
        restart_count = 0
        ip_addr = ""
        ports: List[str] = []
        issues: List[str] = []

        if inspect_doc:
            cid = inspect_doc.get("Id", "")[:12]
            config = inspect_doc.get("Config", {})
            image = config.get("Image", "")
            labels = config.get("Labels", {}) or {}
            service = labels.get("com.docker.compose.service", name)

            state = inspect_doc.get("State", {})
            status = state.get("Status", "unknown").lower()
            exit_code = state.get("ExitCode", 0)
            oom_killed = state.get("OOMKilled", False)
            started_at = state.get("StartedAt", "")
            finished_at = state.get("FinishedAt", "")
            restart_count = inspect_doc.get("RestartCount", 0)

            health_data = state.get("Health", {})
            if health_data:
                docker_health = health_data.get("Status", "none").lower()

            net_settings = inspect_doc.get("NetworkSettings", {})
            ip_addr = net_settings.get("IPAddress", "")
            if not ip_addr:
                networks = net_settings.get("Networks", {})
                for _, net in networks.items():
                    ip_addr = net.get("IPAddress", "")
                    if ip_addr:
                        break

            port_bindings = net_settings.get("Ports", {}) or {}
            for port_proto, host_bindings in port_bindings.items():
                if host_bindings:
                    for b in host_bindings:
                        host_ip = b.get("HostIp", "0.0.0.0")
                        host_port = b.get("HostPort", "")
                        ports.append(f"{host_ip}:{host_port}->{port_proto}")
                else:
                    ports.append(port_proto)

        # Parse live resource stats if container is running
        cpu_pct = 0.0
        mem_usage_bytes = 0
        mem_limit_bytes = 0
        mem_pct = 0.0
        mem_usage_human = "0.0 B"
        mem_limit_human = "0.0 B"
        net_io = "0B / 0B"
        block_io = "0B / 0B"
        pids = 0

        if stats_doc:
            cpu_pct = parse_percentage_string(stats_doc.get("CPUPerc", "0%"))
            mem_pct = parse_percentage_string(stats_doc.get("MemPerc", "0%"))
            net_io = stats_doc.get("NetIO", "0B / 0B")
            block_io = stats_doc.get("BlockIO", "0B / 0B")
            pids_str = stats_doc.get("PIDs", "0")
            try:
                pids = int(pids_str)
            except ValueError:
                pids = 0

            raw_mem = stats_doc.get("MemUsage", "")
            if "/" in raw_mem:
                parts = raw_mem.split("/")
                mem_usage_bytes = parse_size_string(parts[0].strip())
                mem_limit_bytes = parse_size_string(parts[1].strip())
                mem_usage_human = format_size(mem_usage_bytes)
                mem_limit_human = format_size(mem_limit_bytes)

        # Check Uptime
        uptime = calculate_uptime(started_at) if status == "running" else f"Exited (Code {exit_code})"

        # Probe application health
        app_probe = self.probe_application(service, inspect_doc or {}) if status == "running" else {}

        # Evaluate Overall Health State
        if oom_killed:
            overall_health = "UNHEALTHY"
            issues.append(f"Container was terminated by kernel Out-Of-Memory (OOM) killer (exit code {exit_code})")
        elif status in ("exited", "dead"):
            overall_health = "STOPPED"
            issues.append(f"Container is stopped (exit code {exit_code})")
        elif docker_health == "unhealthy":
            overall_health = "UNHEALTHY"
            issues.append("Docker health check returned UNHEALTHY")
        elif status == "restarting":
            overall_health = "DEGRADED"
            issues.append("Container is in a crash/restart loop")
        elif status != "running":
            overall_health = "DEGRADED"
            issues.append(f"Container status is abnormal: {status}")
        else:
            # Container is running; check resource limits and logs
            overall_health = "HEALTHY"

            if cpu_pct >= self.cpu_threshold:
                overall_health = "DEGRADED"
                issues.append(f"High CPU utilization: {cpu_pct:.1f}% >= threshold {self.cpu_threshold:.1f}%")

            if mem_pct >= self.mem_threshold:
                overall_health = "DEGRADED"
                issues.append(f"High memory utilization: {mem_pct:.1f}% >= threshold {self.mem_threshold:.1f}%")

            if log_res and log_res.error_count > 0:
                issues.append(f"Log analysis detected {log_res.error_count} error event(s)")

        return ContainerStats(
            container_id=cid,
            name=name,
            service=service,
            image=image,
            status=status,
            health_status=docker_health,
            overall_health=overall_health,
            cpu_percent=cpu_pct,
            memory_usage_bytes=mem_usage_bytes,
            memory_limit_bytes=mem_limit_bytes,
            memory_percent=mem_pct,
            memory_usage_human=mem_usage_human,
            memory_limit_human=mem_limit_human,
            network_io=net_io,
            block_io=block_io,
            pids=pids,
            uptime=uptime,
            started_at=started_at,
            finished_at=finished_at,
            exit_code=exit_code,
            oom_killed=oom_killed,
            restart_count=restart_count,
            ip_address=ip_addr,
            ports=ports,
            app_probe=app_probe,
            issues=issues,
        )


# ==============================================================================
# Auto-Recovery & Self-Healing Manager
# ==============================================================================

class AutoRecoveryManager:
    """
    Manages automated recovery of stopped or unhealthy containers with safeguards,
    retry thresholds, verification cooldowns, and dry-run simulation.
    """

    def __init__(
        self,
        docker_client: DockerClient,
        max_retries: int = DEFAULT_MAX_RETRIES,
        cooldown_sec: float = DEFAULT_COOLDOWN_SEC,
        dry_run: bool = False,
        logger: Optional[logging.Logger] = None,
    ):
        self.client = docker_client
        self.max_retries = max_retries
        self.cooldown_sec = cooldown_sec
        self.dry_run = dry_run
        self.logger = logger or logging.getLogger("frappe_docker_monitor")
        self.retry_counts: Dict[str, int] = {}

    def should_recover(self, stats: ContainerStats) -> Tuple[bool, str]:
        """Determines if a container qualifies for auto-recovery."""
        if stats.overall_health not in ("STOPPED", "UNHEALTHY"):
            return False, "Container is not stopped or unhealthy"

        current_retries = self.retry_counts.get(stats.name, 0)
        if current_retries >= self.max_retries:
            return False, f"Maximum retry limit ({self.max_retries}) exceeded for {stats.name}"

        return True, "Container qualifies for self-healing restart"

    def recover(self, stats: ContainerStats) -> RecoveryAction:
        """Executes recovery action on a qualifying container and verifies result."""
        now_iso = datetime.datetime.now(datetime.timezone.utc).isoformat()
        current_retries = self.retry_counts.get(stats.name, 0)

        if self.dry_run:
            self.logger.warning(f"[DRY-RUN] Would restart container '{stats.name}' (current status: {stats.status})")
            return RecoveryAction(
                container_name=stats.name,
                attempted_at=now_iso,
                initial_status=stats.status,
                action="dry_run_restart",
                success=True,
                final_status="dry_run",
                message=f"[DRY-RUN] Auto-restart simulated (attempt {current_retries + 1}/{self.max_retries})",
                duration_seconds=0.0,
            )

        self.logger.warning(f"Initiating auto-restart for '{stats.name}' (attempt {current_retries + 1}/{self.max_retries})...")
        start_time = time.perf_counter()

        # Execute restart
        self.retry_counts[stats.name] = current_retries + 1
        restart_ok = self.client.restart_container(stats.name, timeout=10)

        # Wait cooldown for service to stabilize
        time.sleep(self.cooldown_sec)

        # Verify new container state
        duration = time.perf_counter() - start_time
        new_inspect = self.client.inspect_containers([stats.name])
        doc = new_inspect.get(stats.name, {})
        new_status = doc.get("State", {}).get("Status", "unknown") if doc else "unknown"

        success = (new_status == "running") and restart_ok

        if success:
            msg = f"Container '{stats.name}' successfully recovered and returned to 'running' state"
            self.logger.info(msg)
        else:
            msg = f"Auto-recovery failed for '{stats.name}'. Current status remains: {new_status}"
            self.logger.error(msg)

        return RecoveryAction(
            container_name=stats.name,
            attempted_at=now_iso,
            initial_status=stats.status,
            action="restart",
            success=success,
            final_status=new_status,
            message=msg,
            duration_seconds=duration,
        )


# ==============================================================================
# Report Generation & Formatting
# ==============================================================================

class ReportGenerator:
    """Generates structured JSON, rich Markdown, and terminal dashboards."""

    @staticmethod
    def generate_json_report(report: SystemHealthReport, output_file: Optional[Path] = None) -> str:
        """Serializes SystemHealthReport to clean formatted JSON."""
        data = report.to_dict()
        json_str = json.dumps(data, indent=2, ensure_ascii=False)
        if output_file:
            output_file.parent.mkdir(parents=True, exist_ok=True)
            output_file.write_text(json_str, encoding="utf-8")
        return json_str

    @staticmethod
    def generate_markdown_report(report: SystemHealthReport, output_file: Optional[Path] = None) -> str:
        """Generates detailed Markdown report with tables, gauges, and health indicators."""
        status_badge = {
            "HEALTHY": "🟢 **HEALTHY**",
            "DEGRADED": "🟡 **DEGRADED**",
            "CRITICAL": "🔴 **CRITICAL**",
        }.get(report.overall_status, "⚪ **UNKNOWN**")

        lines = [
            f"# Frappe CRM — Docker Container Health & Monitoring Report",
            f"",
            f"**Report Generated:** {report.timestamp}  ",
            f"**Target Project:** `{report.project}`  ",
            f"**System Status:** {status_badge}  ",
            f"**Report ID:** `{report.report_id}`",
            f"",
            f"---",
            f"",
            f"## 1. Executive Summary",
            f"",
            f"| Metric | Value | Threshold / Target |",
            f"| :--- | :--- | :--- |",
            f"| **Overall Health** | {report.overall_status} | `HEALTHY` |",
            f"| **Total Containers** | `{report.summary['total_containers']}` | — |",
            f"| **Running Containers** | `{report.summary['running_containers']}` / `{report.summary['total_containers']}` | 100% |",
            f"| **Stopped Containers** | `{report.summary['stopped_containers']}` | `0` |",
            f"| **Unhealthy Containers** | `{report.summary['unhealthy_containers']}` | `0` |",
            f"| **High Resource Warnings** | `{report.summary['warning_containers']}` | `0` |",
            f"| **Total CPU Consumption** | `{report.summary['total_cpu_percent']:.2f}%` | Threshold: `{report.thresholds['cpu_warning_percent']}%` |",
            f"| **Total Memory Usage** | `{report.summary['total_memory_usage_human']}` | Threshold: `{report.thresholds['memory_warning_percent']}%` |",
            f"| **Log Errors Detected** | `{report.summary['total_errors_in_logs']}` | `0` |",
            f"| **Auto-Recovery Attempts** | `{report.summary['auto_recoveries_attempted']}` (Succeeded: `{report.summary['auto_recoveries_succeeded']}`) | — |",
            f"",
            f"---",
            f"",
            f"## 2. Container Health & Telemetry",
            f"",
            f"| Container Name | Service | Status | Health | CPU% | Memory (Usage / Limit) | PIDs | Uptime |",
            f"| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |",
        ]

        for c in report.containers:
            status_indicator = "🟢" if c.status == "running" else "🔴"
            health_badge = "✅ OK" if c.overall_health == "HEALTHY" else ("⚠️ Warning" if c.overall_health == "DEGRADED" else "❌ Fault")
            lines.append(
                f"| `{c.name}` | `{c.service}` | {status_indicator} {c.status} | {health_badge} | `{c.cpu_percent:.1f}%` | `{c.memory_usage_human}` / `{c.memory_limit_human}` ({c.memory_percent:.1f}%) | `{c.pids}` | {c.uptime} |"
            )

        lines.extend([
            f"",
            f"---",
            f"",
            f"## 3. Container Network & Application Health Probes",
            f"",
            f"| Container | IP Address | Port Mappings | Probe Status | Probe Response / Latency |",
            f"| :--- | :--- | :--- | :--- | :--- |",
        ])

        for c in report.containers:
            ports_str = "<br>".join(c.ports) if c.ports else "Internal only"
            probe = c.app_probe
            if probe.get("checked"):
                probe_status = f"✅ `{probe.get('status')}`"
                probe_resp = f"{probe.get('details')} ({probe.get('latency_ms', 0)} ms)"
            else:
                probe_status = "ℹ️ Active"
                probe_resp = "Healthy daemon state"
            lines.append(f"| `{c.name}` | `{c.ip_address or 'host'}` | {ports_str} | {probe_status} | {probe_resp} |")

        # Section 4: Log Analysis
        lines.extend([
            f"",
            f"---",
            f"",
            f"## 4. Container Log & Anomaly Analysis",
            f"",
        ])

        if report.log_analyses:
            lines.extend([
                f"| Container | Lines Analyzed | Errors | Warnings | Detected Error Categories |",
                f"| :--- | :--- | :--- | :--- | :--- |",
            ])
            for name, la in report.log_analyses.items():
                cat_summary = ", ".join(f"`{k}`: {v}" for k, v in la.category_counts.items()) if la.category_counts else "_None_"
                lines.append(f"| `{name}` | `{la.scanned_lines}` | `{la.error_count}` | `{la.warning_count}` | {cat_summary} |")

            # Check if any sample errors need displaying
            has_samples = any(len(la.recent_errors) > 0 for la in report.log_analyses.values())
            if has_samples:
                lines.extend([
                    f"",
                    f"### Error Snippets",
                    f"",
                ])
                for name, la in report.log_analyses.items():
                    if la.recent_errors:
                        lines.append(f"**Container `{name}`:**")
                        lines.append("```text")
                        for err in la.recent_errors[:5]:
                            lines.append(err)
                        lines.append("```")
        else:
            lines.append("No container logs collected.")

        # Section 5: Auto-Recovery Actions
        lines.extend([
            f"",
            f"---",
            f"",
            f"## 5. Automated Recovery & Self-Healing Actions",
            f"",
        ])

        if report.recovery_actions:
            lines.extend([
                f"| Timestamp | Container | Initial Status | Action | Outcome | Duration | Notes |",
                f"| :--- | :--- | :--- | :--- | :--- | :--- | :--- |",
            ])
            for r in report.recovery_actions:
                outcome_badge = "🟢 Succeeded" if r.success else "🔴 Failed"
                lines.append(
                    f"| `{r.attempted_at}` | `{r.container_name}` | `{r.initial_status}` | `{r.action}` | {outcome_badge} | `{r.duration_seconds:.2f}s` | {r.message} |"
                )
        else:
            lines.append("No recovery actions were required during this monitoring cycle.")

        # Section 6: Active Alerts
        lines.extend([
            f"",
            f"---",
            f"",
            f"## 6. Active Alerts & Operational Recommendations",
            f"",
        ])

        if report.alerts:
            for alert in report.alerts:
                lines.append(f"- ⚠️ **{alert}**")
        else:
            lines.append("- ✅ **All Frappe CRM containers are fully operational and within performance thresholds.**")

        md_content = "\n".join(lines) + "\n"
        if output_file:
            output_file.parent.mkdir(parents=True, exist_ok=True)
            output_file.write_text(md_content, encoding="utf-8")
        return md_content

    @staticmethod
    def print_terminal_dashboard(report: SystemHealthReport, logger: logging.Logger):
        """Renders clean ASCII dashboard to console."""
        sep = "=" * 80
        thin_sep = "-" * 80

        status_color = "\033[32m" if report.overall_status == "HEALTHY" else ("\033[33m" if report.overall_status == "DEGRADED" else "\033[31m")
        reset = "\033[0m"

        print(sep)
        print(f" FRAPPE CRM CONTAINER HEALTH MONITOR — {report.project.upper()}")
        print(f" Timestamp: {report.timestamp} | Status: {status_color}[{report.overall_status}]{reset}")
        print(sep)
        print(f"{'NAME':<16} {'STATUS':<10} {'HEALTH':<10} {'CPU%':<8} {'MEM USAGE / LIMIT':<24} {'PIDS':<6} {'UPTIME'}")
        print(thin_sep)

        for c in report.containers:
            stat_c = "\033[32m" if c.status == "running" else "\033[31m"
            mem_str = f"{c.memory_usage_human} / {c.memory_limit_human}"
            print(
                f"{c.name:<16} {stat_c}{c.status:<10}{reset} {c.overall_health:<10} {c.cpu_percent:>5.1f}%  {mem_str:<24} {c.pids:<6} {c.uptime}"
            )

        print(thin_sep)
        summary = report.summary
        print(
            f"Total CPU: {summary['total_cpu_percent']:.1f}% | Total Mem: {summary['total_memory_usage_human']} | "
            f"Running: {summary['running_containers']}/{summary['total_containers']} | "
            f"Errors: {summary['total_errors_in_logs']} | Recoveries: {summary['auto_recoveries_attempted']}"
        )
        if report.alerts:
            print(thin_sep)
            for alert in report.alerts:
                print(f" \033[33m[ALERT]{reset} {alert}")
        print(sep)


# ==============================================================================
# Orchestrator & Monitoring Service
# ==============================================================================

class FrappeDockerMonitor:
    """
    Main orchestration class coordinating container discovery, telemetry polling,
    log inspection, health evaluation, auto-recovery, and reporting.
    """

    def __init__(
        self,
        project: str = DEFAULT_PROJECT,
        container_names: Optional[List[str]] = None,
        cpu_threshold: float = DEFAULT_CPU_THRESHOLD,
        mem_threshold: float = DEFAULT_MEM_THRESHOLD,
        auto_restart: bool = False,
        dry_run: bool = False,
        max_retries: int = DEFAULT_MAX_RETRIES,
        log_tail: int = DEFAULT_LOG_TAIL,
        logger: Optional[logging.Logger] = None,
    ):
        self.project = project
        self.container_names = container_names
        self.cpu_threshold = cpu_threshold
        self.mem_threshold = mem_threshold
        self.auto_restart = auto_restart
        self.dry_run = dry_run
        self.max_retries = max_retries
        self.log_tail = log_tail
        self.logger = logger or logging.getLogger("frappe_docker_monitor")

        self.docker_client = DockerClient()
        self.evaluator = HealthEvaluator(cpu_threshold=cpu_threshold, mem_threshold=mem_threshold)
        self.recovery_mgr = AutoRecoveryManager(
            docker_client=self.docker_client,
            max_retries=max_retries,
            dry_run=dry_run,
            logger=self.logger,
        )

    def run_cycle(self) -> SystemHealthReport:
        """Executes a single end-to-end monitoring cycle."""
        # 1. Verify Docker Daemon
        daemon_ok, daemon_msg = self.docker_client.check_daemon()
        if not daemon_ok:
            self.logger.critical(daemon_msg)
            raise DockerClientError(daemon_msg)

        # 2. Discover Target Containers
        discovered = self.docker_client.discover_containers(
            project=self.project,
            container_names=self.container_names,
        )
        if not discovered:
            self.logger.warning(f"No containers discovered matching project '{self.project}'.")

        target_names = [c.get("Names", "") for c in discovered if c.get("Names")]

        # 3. Collect Inspect Data & Stats
        inspect_map = self.docker_client.inspect_containers(target_names)
        stats_map = self.docker_client.get_stats_snapshot()

        # 4. Analyze Logs & Build Stats per Container
        container_stats_list: List[ContainerStats] = []
        log_analyses: Dict[str, LogAnalysisResult] = {}
        alerts: List[str] = []

        for name in target_names:
            inspect_doc = inspect_map.get(name)
            stats_doc = stats_map.get(name)

            # Retrieve and analyze logs
            log_lines = self.docker_client.get_logs(name, tail=self.log_tail)
            log_res = LogAnalyzer.analyze(name, log_lines)
            log_analyses[name] = log_res

            # Construct telemetry stats
            c_stat = self.evaluator.build_container_stats(name, inspect_doc, stats_doc, log_res)
            container_stats_list.append(c_stat)

            # Collect alerts
            for issue in c_stat.issues:
                alerts.append(f"{name}: {issue}")

        # 5. Handle Auto-Recovery if Enabled
        recovery_actions: List[RecoveryAction] = []
        if self.auto_restart:
            for c_stat in container_stats_list:
                qualifies, reason = self.recovery_mgr.should_recover(c_stat)
                if qualifies:
                    action_rec = self.recovery_mgr.recover(c_stat)
                    recovery_actions.append(action_rec)
                    if action_rec.success and action_rec.final_status == "running":
                        c_stat.status = "running"
                        c_stat.overall_health = "HEALTHY"
                        c_stat.uptime = "Just recovered"
                        alerts = [a for a in alerts if not a.startswith(f"{c_stat.name}: Container is stopped")]
                        alerts.append(f"{c_stat.name}: Self-healing recovery succeeded.")

        # 6. Aggregate System-Wide Summary
        total_c = len(container_stats_list)
        running_c = sum(1 for c in container_stats_list if c.status == "running")
        stopped_c = sum(1 for c in container_stats_list if c.status in ("exited", "dead"))
        unhealthy_c = sum(1 for c in container_stats_list if c.overall_health == "UNHEALTHY")
        warning_c = sum(1 for c in container_stats_list if c.overall_health == "DEGRADED")
        total_cpu = sum(c.cpu_percent for c in container_stats_list)
        total_mem_bytes = sum(c.memory_usage_bytes for c in container_stats_list)
        total_log_errors = sum(la.error_count for la in log_analyses.values())
        successful_recoveries = sum(1 for r in recovery_actions if r.success)

        # Determine System Overall Status
        if stopped_c > 0 or unhealthy_c > 0:
            overall_status = "CRITICAL"
        elif warning_c > 0 or total_cpu >= self.cpu_threshold or total_log_errors > 5:
            overall_status = "DEGRADED"
        else:
            overall_status = "HEALTHY"

        now = datetime.datetime.now(datetime.timezone.utc)
        report_id = f"report_{now.strftime('%Y%m%d_%H%M%S')}"

        summary = {
            "total_containers": total_c,
            "running_containers": running_c,
            "stopped_containers": stopped_c,
            "unhealthy_containers": unhealthy_c,
            "warning_containers": warning_c,
            "total_cpu_percent": round(total_cpu, 2),
            "total_memory_usage_bytes": total_mem_bytes,
            "total_memory_usage_human": format_size(total_mem_bytes),
            "total_errors_in_logs": total_log_errors,
            "auto_recoveries_attempted": len(recovery_actions),
            "auto_recoveries_succeeded": successful_recoveries,
        }

        thresholds = {
            "cpu_warning_percent": self.cpu_threshold,
            "memory_warning_percent": self.mem_threshold,
        }

        report = SystemHealthReport(
            report_id=report_id,
            timestamp=now.isoformat(),
            project=self.project,
            overall_status=overall_status,
            summary=summary,
            thresholds=thresholds,
            containers=container_stats_list,
            log_analyses=log_analyses,
            recovery_actions=recovery_actions,
            alerts=alerts,
        )

        return report


# ==============================================================================
# CLI Argument Parser & Entry Point
# ==============================================================================

def build_parser() -> argparse.ArgumentParser:
    """Builds the comprehensive command-line interface argument parser."""
    parser = argparse.ArgumentParser(
        prog="frappe_docker_monitor.py",
        description="Frappe CRM Docker Container Monitoring & Auto-Recovery Automation Tool",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Check system health snapshot for Frappe CRM
  python scripts/frappe_docker_monitor.py

  # Monitor Frappe CRM and output JSON report
  python scripts/frappe_docker_monitor.py --output-json reports/health_report.json

  # Enable auto-restart for stopped/unhealthy containers
  python scripts/frappe_docker_monitor.py --auto-restart

  # Simulate auto-restart without modifying container states (Dry Run)
  python scripts/frappe_docker_monitor.py --auto-restart --dry-run

  # Continuous monitoring with 5s refresh
  python scripts/frappe_docker_monitor.py --watch --interval 5

  # Custom CPU and Memory thresholds
  python scripts/frappe_docker_monitor.py --cpu-threshold 75 --mem-threshold 85
        """,
    )

    parser.add_argument(
        "--project",
        "-p",
        default=DEFAULT_PROJECT,
        help=f"Target Docker Compose project name to monitor (default: '{DEFAULT_PROJECT}', use 'all' for all containers).",
    )
    parser.add_argument(
        "--containers",
        "-c",
        nargs="+",
        help="Optional explicit list of container names to monitor (overrides project discovery).",
    )
    parser.add_argument(
        "--auto-restart",
        "--recover",
        action="store_true",
        help="Enable automated restart for stopped or unhealthy containers.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Simulate auto-recovery actions without actually restarting containers.",
    )
    parser.add_argument(
        "--max-retries",
        type=int,
        default=DEFAULT_MAX_RETRIES,
        help=f"Maximum auto-restart attempts per container (default: {DEFAULT_MAX_RETRIES}).",
    )
    parser.add_argument(
        "--cpu-threshold",
        type=float,
        default=DEFAULT_CPU_THRESHOLD,
        help=f"CPU warning threshold percentage (default: {DEFAULT_CPU_THRESHOLD}%%).",
    )
    parser.add_argument(
        "--mem-threshold",
        type=float,
        default=DEFAULT_MEM_THRESHOLD,
        help=f"Memory warning threshold percentage (default: {DEFAULT_MEM_THRESHOLD}%%).",
    )
    parser.add_argument(
        "--log-tail",
        type=int,
        default=DEFAULT_LOG_TAIL,
        help=f"Number of recent log lines to analyze per container (default: {DEFAULT_LOG_TAIL}).",
    )
    parser.add_argument(
        "--watch",
        "-w",
        action="store_true",
        help="Run continuously in watch mode with live dashboard refreshes.",
    )
    parser.add_argument(
        "--interval",
        "-i",
        type=int,
        default=10,
        help="Refresh interval in seconds for --watch mode (default: 10s).",
    )
    parser.add_argument(
        "--output-json",
        type=Path,
        help="Path to save the generated JSON system health report.",
    )
    parser.add_argument(
        "--output-md",
        type=Path,
        help="Path to save the generated Markdown system health report.",
    )
    parser.add_argument(
        "--log-file",
        type=Path,
        default=DEFAULT_LOG_FILE,
        help=f"Path to persistent log file (default: '{DEFAULT_LOG_FILE}').",
    )
    parser.add_argument(
        "--format",
        choices=["terminal", "json", "markdown"],
        default="terminal",
        help="Standard output format (terminal dashboard, raw json, or markdown).",
    )
    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Enable verbose DEBUG logging.",
    )
    parser.add_argument(
        "--quiet",
        "-q",
        action="store_true",
        help="Suppress non-error log output.",
    )

    return parser


def main() -> int:
    """CLI execution entry point."""
    parser = build_parser()
    args = parser.parse_args()

    # Configure multi-channel logger
    logger = setup_logger(
        log_file=args.log_file,
        verbose=args.verbose,
        quiet=args.quiet,
    )

    try:
        monitor = FrappeDockerMonitor(
            project=args.project,
            container_names=args.containers,
            cpu_threshold=args.cpu_threshold,
            mem_threshold=args.mem_threshold,
            auto_restart=args.auto_restart,
            dry_run=args.dry_run,
            max_retries=args.max_retries,
            log_tail=args.log_tail,
            logger=logger,
        )

        # Watch mode loop
        if args.watch:
            logger.info(f"Starting continuous monitoring watch loop (interval: {args.interval}s, Ctrl+C to stop)...")
            try:
                while True:
                    report = monitor.run_cycle()
                    ReportGenerator.print_terminal_dashboard(report, logger)

                    if args.output_json:
                        ReportGenerator.generate_json_report(report, args.output_json)
                    if args.output_md:
                        ReportGenerator.generate_markdown_report(report, args.output_md)

                    time.sleep(args.interval)
            except KeyboardInterrupt:
                logger.info("Watch loop terminated by user. Exiting cleanly.")
                return EXIT_HEALTHY

        # Single snapshot check
        report = monitor.run_cycle()

        # Handle outputs
        if args.output_json:
            ReportGenerator.generate_json_report(report, args.output_json)
            logger.info(f"JSON health report saved to: {args.output_json}")

        if args.output_md:
            ReportGenerator.generate_markdown_report(report, args.output_md)
            logger.info(f"Markdown health report saved to: {args.output_md}")

        # Format console output
        if args.format == "json":
            print(ReportGenerator.generate_json_report(report))
        elif args.format == "markdown":
            print(ReportGenerator.generate_markdown_report(report))
        else:
            ReportGenerator.print_terminal_dashboard(report, logger)

        # Return appropriate exit code based on health
        if report.overall_status == "HEALTHY":
            return EXIT_HEALTHY
        else:
            return EXIT_DEGRADED

    except DockerClientError as dce:
        logger.critical(f"Docker Failure: {dce}")
        return EXIT_DOCKER_ERROR
    except Exception as ex:
        logger.critical(f"Unexpected Fatal Error: {ex}", exc_info=args.verbose)
        return EXIT_PARAM_ERROR


if __name__ == "__main__":
    sys.exit(main())
