import json
import shutil
from datetime import datetime, timezone
from pathlib import Path

from .config import MonitorConfig
from .models import ContainerStatusReport, RecoveryAction, SystemHealthReport


class HealthReporter:
	"""Generates JSON health reports, rotates old report files, and prints terminal tables."""

	def __init__(self, config: MonitorConfig) -> None:
		self.config = config

	def build_report(
		self,
		container_reports: list[ContainerStatusReport],
		recovery_actions: list[RecoveryAction],
	) -> SystemHealthReport:
		now = datetime.now(timezone.utc)
		running = sum(1 for c in container_reports if c.state.status == "running")
		stopped = sum(1 for c in container_reports if c.state.status != "running")
		unhealthy = sum(
			1
			for c in container_reports
			if c.state.health == "unhealthy" or c.state.app_probe_status == "failed"
		)
		warn_exceeded = sum(1 for c in container_reports if c.threshold_alerts)
		crit_logs = sum(c.log_analysis.critical_errors for c in container_reports)

		if stopped > 0 or unhealthy > 0 or crit_logs > 0:
			cluster_status = "CRITICAL"
		elif (
			warn_exceeded > 0 or any(c.log_analysis.errors > 0 for c in container_reports) or recovery_actions
		):
			cluster_status = "DEGRADED"
		else:
			cluster_status = "HEALTHY"

		summary = {
			"total_containers": len(container_reports),
			"running": running,
			"stopped": stopped,
			"unhealthy": unhealthy,
			"warning_threshold_exceeded": warn_exceeded,
			"critical_log_errors": crit_logs,
		}

		return SystemHealthReport(
			timestamp=now.isoformat(),
			cluster_status=cluster_status,
			summary=summary,
			containers=container_reports,
			recovery_actions=recovery_actions,
		)

	def save_json_report(self, report: SystemHealthReport) -> Path:
		ts_slug = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
		report_path = self.config.reports_dir / f"health_report_{ts_slug}.json"
		latest_path = self.config.reports_dir / "latest_health_report.json"

		payload = json.dumps(report.to_dict(), indent=2)
		report_path.write_text(payload, encoding="utf-8")
		shutil.copyfile(report_path, latest_path)

		self._prune_old_reports()
		return report_path

	def _prune_old_reports(self) -> None:
		reports = sorted(self.config.reports_dir.glob("health_report_*.json"))
		excess = len(reports) - self.config.max_reports_kept
		for old_file in reports[: max(0, excess)]:
			old_file.unlink(missing_ok=True)

	def print_terminal_summary(self, report: SystemHealthReport) -> None:
		line = "─" * 98
		print(f"\n{line}")
		print(f" FrappeCRM Docker Health Audit | Status: {report.cluster_status} | {report.timestamp}")
		print(line)
		print(
			f" {'CONTAINER':<18} {'STATE':<10} {'PROBE':<9} {'CPU %':<8} "
			f"{'MEM USAGE':<22} {'MEM %':<8} {'RESTARTS':<8} {'LOG ERR'}"
		)
		print(line)
		for c in report.containers:
			mem_str = f"{c.metrics.memory_used_human} / {c.metrics.memory_limit_human}"
			errs = c.log_analysis.critical_errors + c.log_analysis.errors
			print(
				f" {c.name:<18} {c.state.status:<10} {c.state.app_probe_status:<9} "
				f"{c.metrics.cpu_percent:<8.2f} {mem_str:<22} {c.metrics.memory_percent:<8.2f} "
				f"{c.state.restart_count:<8} {errs}"
			)
		print(f"{line}\n")
