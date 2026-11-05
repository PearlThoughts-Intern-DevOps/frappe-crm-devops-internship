"""Docker Container Monitoring and Auto-Recovery Tool for Frappe CRM.

Senior Google Staff DevOps / SRE implementation providing container discovery,
health monitoring, CPU/Memory telemetry, transparent log analysis, timestamped
JSON reporting, and policy-governed isolated auto-recovery.
"""

from __future__ import annotations

import argparse
import datetime
import json
import logging
import os
import re
import sys
from pathlib import Path
from typing import Any

try:
	from docker.errors import DockerException, NotFound
	from docker.models.containers import Container

	import docker
except ImportError:  # pragma: no cover
	docker = None  # type: ignore[assignment]
	DockerException = Exception  # type: ignore[misc,assignment]
	NotFound = Exception  # type: ignore[misc,assignment]
	Container = Any  # type: ignore[misc,assignment]

# Exit Codes
EXIT_HEALTHY = 0
EXIT_DEGRADED = 1
EXIT_INVALID_CONFIG = 2
EXIT_DOCKER_ERROR = 3
EXIT_SAFETY_VIOLATION = 4

# Sensitive credential patterns for log masking
SECRET_PATTERNS = [
	re.compile(
		r"(password|passwd|pwd|secret|token|api_key|auth_token|root_password)\s*[:=]\s*([^\s,;&]+)",
		re.IGNORECASE,
	),
	re.compile(r"(--mariadb-root-password|--password|-p)\s+([^\s]+)", re.IGNORECASE),
	re.compile(r"(mysql://[^:]+:)([^@]+)(@)", re.IGNORECASE),
]

# Sensitive containers that can NEVER be auto-recovered under any circumstances
PROHIBITED_RECOVERY_PREFIXES = ("crm-frappe", "crm-mariadb", "crm-redis")
PROHIBITED_COMPOSE_PROJECTS = ("crm", "crm-production", "crm-staging")

logger = logging.getLogger("docker_monitor")


def setup_logging(verbose: bool = False) -> None:
	"""Configure application logging for console output."""
	level = logging.DEBUG if verbose else logging.INFO
	handler = logging.StreamHandler(sys.stdout)
	formatter = logging.Formatter("[%(asctime)s] [%(levelname)s] %(message)s", datefmt="%Y-%m-%dT%H:%M:%S%z")
	handler.setFormatter(formatter)
	logger.setLevel(level)
	logger.handlers = [handler]


def mask_sensitive_data(text: str) -> str:
	"""Mask passwords, tokens, and secrets from log strings."""
	masked = text
	for pattern in SECRET_PATTERNS:
		masked = pattern.sub(r"\1=******", masked)
	return masked


def safe_resolve_path(base_dir: Path, target_path: str) -> Path:
	"""Safely resolve child path within a base directory, rejecting path traversal."""
	resolved = (base_dir / target_path).resolve()
	base_resolved = base_dir.resolve()
	if not str(resolved).startswith(str(base_resolved)):
		msg = f"Path traversal attempt detected: '{target_path}'"
		raise ValueError(msg)
	return resolved


class DockerMonitor:
	"""Enterprise-grade Docker Monitoring and Policy-Governed Auto-Recovery Engine."""

	def __init__(self, config: dict[str, Any] | None = None, client: Any | None = None):
		self.config = self._sanitize_config(config or {})
		self._client = client
		self._recovery_history: dict[str, list[datetime.datetime]] = {}

	def _sanitize_config(self, raw_config: dict[str, Any]) -> dict[str, Any]:
		"""Validate and apply defaults to configuration."""
		return {
			"compose_project": raw_config.get("compose_project", "crm"),
			"container_names": raw_config.get("container_names", []),
			"report_dir": raw_config.get("report_dir", "reports"),
			"log_tail_lines": int(raw_config.get("log_tail_lines", 100)),
			"cpu_warning_threshold_percent": float(raw_config.get("cpu_warning_threshold_percent", 80.0)),
			"memory_warning_threshold_percent": float(
				raw_config.get("memory_warning_threshold_percent", 85.0)
			),
			"restart_warning_threshold": int(raw_config.get("restart_warning_threshold", 3)),
			"auto_recovery_enabled": bool(raw_config.get("auto_recovery_enabled", False)),
			"allowed_recovery_containers": list(
				raw_config.get("allowed_recovery_containers", ["crm-monitor-test-service"])
			),
			"max_recovery_attempts": int(raw_config.get("max_recovery_attempts", 3)),
			"recovery_cooldown_seconds": int(raw_config.get("recovery_cooldown_seconds", 60)),
		}

	def get_client(self) -> Any:
		"""Obtain or initialize the Docker SDK client."""
		if self._client is not None:
			return self._client
		if docker is None:
			msg = "Docker SDK for Python ('docker') is not installed. Run 'pip install docker'."
			raise DockerException(msg)
		try:
			self._client = docker.from_env()
			self._client.ping()
			return self._client
		except Exception as exc:
			logger.error("Failed to connect to Docker daemon: %s", exc)
			raise DockerException(f"Cannot connect to Docker daemon: {exc}") from exc

	def discover_containers(self) -> list[Container]:
		"""Discover containers based on Compose project label or explicit container names."""
		client = self.get_client()
		explicit_names = set(self.config.get("container_names", []))
		compose_project = self.config.get("compose_project", "crm")

		try:
			all_containers = client.containers.list(all=True)
		except Exception as exc:
			logger.error("Failed to list Docker containers: %s", exc)
			raise DockerException(f"Error listing containers: {exc}") from exc

		discovered: list[Container] = []
		for c in all_containers:
			c_name = c.name
			c_labels = c.attrs.get("Config", {}).get("Labels") or {}

			# Match explicit names if provided
			if explicit_names and c_name in explicit_names:
				discovered.append(c)
				continue

			# Otherwise match compose project label
			if compose_project and c_labels.get("com.docker.compose.project") == compose_project:
				discovered.append(c)

		return discovered

	def calculate_cpu_percent(self, stats: dict[str, Any]) -> float | None:
		"""Calculate container CPU percentage from stats payload with zero-division safety."""
		try:
			cpu_stats = stats.get("cpu_stats", {})
			precpu_stats = stats.get("precpu_stats", {})

			total_usage = cpu_stats.get("cpu_usage", {}).get("total_usage", 0)
			pre_total_usage = precpu_stats.get("cpu_usage", {}).get("total_usage", 0)
			cpu_delta = total_usage - pre_total_usage

			system_usage = cpu_stats.get("system_cpu_usage", 0)
			pre_system_usage = precpu_stats.get("system_cpu_usage", 0)
			system_delta = system_usage - pre_system_usage

			online_cpus = cpu_stats.get("online_cpus")
			if not online_cpus:
				percpu = cpu_stats.get("cpu_usage", {}).get("percpu_usage") or []
				online_cpus = len(percpu) if percpu else 1

			if system_delta > 0.0 and cpu_delta >= 0.0:
				cpu_percent = (cpu_delta / system_delta) * online_cpus * 100.0
				return round(cpu_percent, 2)
			return 0.0
		except Exception as exc:
			logger.debug("CPU percent calculation failed: %s", exc)
			return None

	def calculate_memory_metrics(self, stats: dict[str, Any]) -> tuple[int | None, int | None, float | None]:
		"""Calculate container memory usage, limit, and percentage accounting for cgroup cache."""
		try:
			mem_stats = stats.get("memory_stats", {})
			usage = mem_stats.get("usage")
			limit = mem_stats.get("limit")

			if usage is None or limit is None or limit <= 0:
				return None, None, None

			stats_detail = mem_stats.get("stats", {})
			# Accounting for inactive file / cache across cgroups v1 and v2
			cache = (
				stats_detail.get("inactive_file")
				or stats_detail.get("total_inactive_file")
				or stats_detail.get("cache")
				or 0
			)
			used_memory = max(0, usage - cache)
			mem_percent = round((used_memory / limit) * 100.0, 2)
			return used_memory, limit, mem_percent
		except Exception as exc:
			logger.debug("Memory metric calculation failed: %s", exc)
			return None, None, None

	def analyze_container_logs(self, container: Container) -> dict[str, Any]:
		"""Extract and analyze recent container logs for transparent error detection."""
		tail_lines = self.config.get("log_tail_lines", 100)
		result: dict[str, Any] = {
			"error_count": 0,
			"warning_count": 0,
			"sample_errors": [],
		}

		try:
			raw_logs = container.logs(tail=tail_lines, timestamps=True)
			log_text = (
				raw_logs.decode("utf-8", errors="replace") if isinstance(raw_logs, bytes) else str(raw_logs)
			)
		except Exception as exc:
			logger.debug("Failed to read logs for container %s: %s", container.name, exc)
			result["sample_errors"].append(f"Log retrieval failed: {exc}")
			return result

		error_indicators = (
			"error",
			"critical",
			"fatal",
			"traceback",
			"exception",
			"connection refused",
			"out of memory",
		)
		warning_indicators = ("warning", "warn")

		sample_errors: list[str] = []
		for line in log_text.splitlines():
			lower_line = line.lower()
			if any(ind in lower_line for ind in error_indicators):
				result["error_count"] += 1
				sanitized_line = mask_sensitive_data(line.strip())
				if len(sample_errors) < 3 and sanitized_line not in sample_errors:
					sample_errors.append(sanitized_line)
			elif any(ind in lower_line for ind in warning_indicators):
				result["warning_count"] += 1

		result["sample_errors"] = sample_errors
		return result

	def inspect_container(self, container: Container) -> dict[str, Any]:
		"""Collect comprehensive metrics and state for a single container."""
		c_name = container.name
		c_id = container.id[:12] if container.id else "unknown"

		# Reload container attributes to ensure freshest state
		try:
			container.reload()
		except Exception as exc:
			logger.warning("Failed to refresh attributes for container %s: %s", c_name, exc)

		attrs = container.attrs or {}
		state = attrs.get("State", {})
		config = attrs.get("Config", {})

		image = config.get("Image", "unknown")
		status = state.get("Status", container.status or "unknown")
		exit_code = state.get("ExitCode")
		created_at = attrs.get("Created")
		started_at = state.get("StartedAt")
		restart_count = attrs.get("RestartCount", 0)

		# Health check status determination
		health_dict = state.get("Health")
		if health_dict and "Status" in health_dict:
			health_status = health_dict["Status"]
		else:
			health_status = "not_configured"

		# Resource statistics
		cpu_percent = None
		mem_usage_bytes = None
		mem_limit_bytes = None
		mem_percent = None
		issues: list[str] = []

		if status == "running":
			try:
				stats = container.stats(stream=False)
				cpu_percent = self.calculate_cpu_percent(stats)
				mem_usage_bytes, mem_limit_bytes, mem_percent = self.calculate_memory_metrics(stats)
			except Exception as exc:
				logger.debug("Failed to stream stats for %s: %s", c_name, exc)
				issues.append(f"Resource metrics unavailable: {exc}")
		else:
			issues.append(f"Container is not running (state: {status}, exit_code: {exit_code})")

		# Threshold evaluations
		if health_status == "unhealthy":
			issues.append("Container reported unhealthy by Docker health check")
		if restart_count >= self.config["restart_warning_threshold"]:
			issues.append(f"High restart count detected ({restart_count} restarts)")
		if cpu_percent is not None and cpu_percent >= self.config["cpu_warning_threshold_percent"]:
			issues.append(
				f"High CPU utilization: {cpu_percent}% >= threshold {self.config['cpu_warning_threshold_percent']}%"
			)
		if mem_percent is not None and mem_percent >= self.config["memory_warning_threshold_percent"]:
			issues.append(
				f"High Memory utilization: {mem_percent}% >= threshold {self.config['memory_warning_threshold_percent']}%"
			)

		# Log analysis
		log_analysis = self.analyze_container_logs(container)

		return {
			"name": c_name,
			"id": c_id,
			"image": image,
			"status": status,
			"health_status": health_status,
			"cpu_percent": cpu_percent,
			"memory_usage_bytes": mem_usage_bytes,
			"memory_limit_bytes": mem_limit_bytes,
			"memory_percent": mem_percent,
			"restart_count": restart_count,
			"exit_code": exit_code,
			"created_at": created_at,
			"started_at": started_at,
			"log_analysis": log_analysis,
			"issues": issues,
		}

	def attempt_recovery(self, container_data: dict[str, Any], container_obj: Container) -> dict[str, Any]:
		"""Safely execute auto-recovery on an isolated test container with strict safety gates."""
		c_name = container_data["name"]
		now = datetime.datetime.now(datetime.timezone.utc)

		# Mandatory Safety Gate 1: Check prohibited original CRM container names
		if (
			any(c_name.startswith(prefix) for prefix in PROHIBITED_RECOVERY_PREFIXES)
			or c_name in PROHIBITED_RECOVERY_PREFIXES
		):
			msg = f"SAFETY VIOLATION: Auto-recovery strictly prohibited on original CRM container '{c_name}'"
			logger.critical(msg)
			return {
				"container": c_name,
				"action": "blocked",
				"status": "SAFETY_VIOLATION",
				"error": msg,
				"timestamp": now.isoformat(),
			}

		# Mandatory Safety Gate 2: Verify explicit allowlist
		allowed = self.config.get("allowed_recovery_containers", [])
		if c_name not in allowed:
			msg = f"POLICY BLOCKED: Container '{c_name}' is not in allowed_recovery_containers list"
			logger.warning(msg)
			return {
				"container": c_name,
				"action": "skipped",
				"status": "NOT_ALLOWLISTED",
				"error": msg,
				"timestamp": now.isoformat(),
			}

		# Mandatory Safety Gate 3: Check Compose project
		c_labels = container_obj.attrs.get("Config", {}).get("Labels") or {}
		c_proj = c_labels.get("com.docker.compose.project", "")
		if c_proj in PROHIBITED_COMPOSE_PROJECTS:
			msg = f"SAFETY VIOLATION: Auto-recovery forbidden for containers under compose project '{c_proj}'"
			logger.critical(msg)
			return {
				"container": c_name,
				"action": "blocked",
				"status": "SAFETY_VIOLATION",
				"error": msg,
				"timestamp": now.isoformat(),
			}

		# Gate 4: Cooldown & Attempt Limit
		history = self._recovery_history.setdefault(c_name, [])
		cooldown_sec = self.config.get("recovery_cooldown_seconds", 60)
		max_attempts = self.config.get("max_recovery_attempts", 3)

		# Filter history to recent window
		cutoff = now - datetime.timedelta(seconds=cooldown_sec * 5)
		history = [ts for ts in history if ts > cutoff]
		self._recovery_history[c_name] = history

		if len(history) >= max_attempts:
			msg = f"Rate limit reached: {len(history)} recovery attempts within cooldown window"
			logger.warning("Container %s exceeded max recovery attempts (%d)", c_name, max_attempts)
			return {
				"container": c_name,
				"action": "skipped",
				"status": "MAX_ATTEMPTS_EXCEEDED",
				"error": msg,
				"timestamp": now.isoformat(),
			}

		if history and (now - history[-1]).total_seconds() < cooldown_sec:
			msg = f"Cooldown in effect ({int((now - history[-1]).total_seconds())}s < {cooldown_sec}s)"
			logger.info("Container %s is in recovery cooldown", c_name)
			return {
				"container": c_name,
				"action": "skipped",
				"status": "COOLDOWN_ACTIVE",
				"error": msg,
				"timestamp": now.isoformat(),
			}

		# Execute recovery restart
		logger.warning("Initiating auto-recovery restart on verified test container '%s'...", c_name)
		try:
			container_obj.restart(timeout=10)
			history.append(now)
			logger.info("Successfully restarted container '%s'", c_name)
			return {
				"container": c_name,
				"action": "restart",
				"status": "SUCCESS",
				"timestamp": now.isoformat(),
				"attempt_number": len(history),
			}
		except Exception as exc:
			logger.error("Auto-recovery restart failed on container %s: %s", c_name, exc)
			return {
				"container": c_name,
				"action": "restart",
				"status": "FAILED",
				"error": str(exc),
				"timestamp": now.isoformat(),
			}

	def run_monitoring_cycle(self, trigger_recovery: bool | None = None) -> tuple[int, dict[str, Any]]:
		"""Execute a full monitoring pass, analyze health, execute optional recovery, and return report."""
		now = datetime.datetime.now(datetime.timezone.utc)
		report: dict[str, Any] = {
			"report_version": "1.0",
			"generated_at": now.isoformat(),
			"overall_status": "healthy",
			"monitoring_summary": {
				"total_containers": 0,
				"running": 0,
				"stopped": 0,
				"unhealthy": 0,
				"unknown": 0,
			},
			"containers": [],
			"auto_recovery": {
				"enabled": self.config.get("auto_recovery_enabled", False)
				if trigger_recovery is None
				else trigger_recovery,
				"actions_taken": [],
			},
			"monitoring_errors": [],
		}

		# Discover containers
		try:
			containers = self.discover_containers()
		except DockerException as exc:
			report["overall_status"] = "error"
			report["monitoring_errors"].append(str(exc))
			return EXIT_DOCKER_ERROR, report

		if not containers:
			msg = f"No containers matched project='{self.config.get('compose_project')}' or explicit names."
			logger.warning(msg)
			report["monitoring_errors"].append(msg)
			report["overall_status"] = "degraded"
			return EXIT_DEGRADED, report

		recovery_enabled = report["auto_recovery"]["enabled"]
		has_unhealthy = False
		has_stopped = False

		for c in containers:
			c_info = self.inspect_container(c)
			report["containers"].append(c_info)
			report["monitoring_summary"]["total_containers"] += 1

			status = c_info["status"]
			health = c_info["health_status"]

			if status == "running":
				report["monitoring_summary"]["running"] += 1
			elif status in ("exited", "dead", "stopped"):
				report["monitoring_summary"]["stopped"] += 1
				has_stopped = True
			else:
				report["monitoring_summary"]["unknown"] += 1

			if health == "unhealthy":
				report["monitoring_summary"]["unhealthy"] += 1
				has_unhealthy = True

			# Candidate for auto-recovery if stopped or unhealthy
			if recovery_enabled and (status != "running" or health == "unhealthy"):
				action_record = self.attempt_recovery(c_info, c)
				report["auto_recovery"]["actions_taken"].append(action_record)
				if action_record.get("status") == "SAFETY_VIOLATION":
					report["overall_status"] = "error"
					return EXIT_SAFETY_VIOLATION, report

		# Determine overall status
		if has_unhealthy or has_stopped:
			report["overall_status"] = "degraded"
			exit_code = EXIT_DEGRADED
		else:
			report["overall_status"] = "healthy"
			exit_code = EXIT_HEALTHY

		return exit_code, report

	def save_report(self, report: dict[str, Any], output_dir: str | Path | None = None) -> Path:
		"""Save report atomically to timestamped JSON file without exposing credentials."""
		target_dir = Path(output_dir or self.config.get("report_dir", "reports")).resolve()
		target_dir.mkdir(parents=True, exist_ok=True)

		now_str = datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%d_%H%M%S")
		report_path = target_dir / f"docker_health_report_{now_str}.json"
		temp_path = target_dir / f".tmp_{report_path.name}"

		serialized = json.dumps(report, indent=2)
		temp_path.write_text(serialized, encoding="utf-8")
		temp_path.replace(report_path)
		logger.info("Health report saved to %s", report_path)
		return report_path


def print_cli_summary(report: dict[str, Any]) -> None:
	"""Print a clean, structured terminal summary of the health report."""
	summary = report.get("monitoring_summary", {})
	overall = report.get("overall_status", "unknown").upper()

	print("\n" + "=" * 78)
	print(f" FRAPPE CRM DOCKER MONITORING REPORT — STATUS: {overall}")
	print("=" * 78)
	print(f" Generated: {report.get('generated_at')}")
	print(
		f" Containers: Total={summary.get('total_containers', 0)} | Running={summary.get('running', 0)} | "
		f"Stopped={summary.get('stopped', 0)} | Unhealthy={summary.get('unhealthy', 0)}"
	)
	print("-" * 78)
	print(f"{'CONTAINER':<28} {'STATE':<10} {'HEALTH':<15} {'CPU%':<8} {'MEM%':<8} {'RESTARTS'}")
	print("-" * 78)

	for c in report.get("containers", []):
		name = c["name"][:27]
		status = c["status"][:9]
		health = c["health_status"][:14]
		cpu = f"{c['cpu_percent']}%" if c["cpu_percent"] is not None else "-"
		mem = f"{c['memory_percent']}%" if c["memory_percent"] is not None else "-"
		restarts = str(c["restart_count"])
		print(f"{name:<28} {status:<10} {health:<15} {cpu:<8} {mem:<8} {restarts}")

		if c.get("issues"):
			for issue in c["issues"]:
				print(f"   [!] Issue: {issue}")

	print("-" * 78)
	recovery = report.get("auto_recovery", {})
	print(f" Auto-Recovery Enabled: {recovery.get('enabled')}")
	if recovery.get("actions_taken"):
		print(" Actions Taken:")
		for act in recovery["actions_taken"]:
			print(
				f"   - {act.get('container')}: {act.get('action')} ({act.get('status')}) - {act.get('error', 'OK')}"
			)
	print("=" * 78 + "\n")


def parse_args(args: list[str] | None = None) -> argparse.Namespace:
	"""Parse command-line interface arguments."""
	parser = argparse.ArgumentParser(
		description="Docker Container Monitoring and Auto-Recovery Tool for Frappe CRM."
	)
	subparsers = parser.add_subparsers(dest="command", help="Available subcommands")

	# Subcommand 'monitor'
	monitor_parser = subparsers.add_parser("monitor", help="Run monitoring cycle on Docker containers")
	monitor_parser.add_argument("--config", type=str, help="Path to JSON configuration file")
	monitor_parser.add_argument(
		"--compose-project", type=str, help="Docker Compose project name to filter (default: crm)"
	)
	monitor_parser.add_argument(
		"--report", action="store_true", help="Generate and save JSON health report file"
	)
	monitor_parser.add_argument(
		"--report-dir", type=str, help="Directory to save JSON reports (default: reports)"
	)
	monitor_parser.add_argument(
		"--auto-recovery",
		action="store_true",
		help="Enable policy-governed auto-recovery on allowlisted test containers",
	)
	monitor_parser.add_argument("--json", action="store_true", help="Output raw JSON report to stdout")
	monitor_parser.add_argument("--verbose", action="store_true", help="Enable verbose debug logging")

	return parser.parse_args(args)


def main(args: list[str] | None = None) -> int:
	"""Main entry point for Docker Monitoring CLI."""
	parsed = parse_args(args)
	setup_logging(verbose=getattr(parsed, "verbose", False))

	# Default to monitor if no subcommand specified
	if not parsed.command:
		parsed.command = "monitor"

	config: dict[str, Any] = {}
	if getattr(parsed, "config", None):
		config_path = Path(parsed.config).resolve()
		if not config_path.is_file():
			logger.error("Configuration file not found: %s", config_path)
			return EXIT_INVALID_CONFIG
		try:
			config = json.loads(config_path.read_text(encoding="utf-8"))
		except Exception as exc:
			logger.error("Failed to parse configuration file: %s", exc)
			return EXIT_INVALID_CONFIG

	# Override config with CLI flags
	if getattr(parsed, "compose_project", None):
		config["compose_project"] = parsed.compose_project
	if getattr(parsed, "report_dir", None):
		config["report_dir"] = parsed.report_dir
	if getattr(parsed, "auto_recovery", False):
		config["auto_recovery_enabled"] = True

	try:
		monitor = DockerMonitor(config=config)
		exit_code, report = monitor.run_monitoring_cycle()

		if getattr(parsed, "report", False):
			monitor.save_report(report)

		if getattr(parsed, "json", False):
			print(json.dumps(report, indent=2))
		else:
			print_cli_summary(report)

		return exit_code
	except DockerException as exc:
		logger.error("Docker infrastructure error: %s", exc)
		return EXIT_DOCKER_ERROR
	except Exception as exc:
		logger.critical("Unexpected error during monitoring execution: %s", exc, exc_info=True)
		return EXIT_INVALID_CONFIG


if __name__ == "__main__":
	sys.exit(main())
