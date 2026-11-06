from typing import Any

from .config import MonitorConfig
from .engine import DockerEngineClient
from .models import ContainerHealthInfo, ContainerMetrics


def format_bytes(num_bytes: int) -> str:
	if num_bytes >= 1024**3:
		return f"{num_bytes / (1024**3):.2f} GiB"
	return f"{num_bytes / (1024**2):.2f} MiB"


class MetricsCollector:
	"""Collects container state, cgroup metrics, and executes active liveness probes."""

	def __init__(self, engine: DockerEngineClient, config: MonitorConfig) -> None:
		self.engine = engine
		self.config = config

	def collect_health_and_metrics(
		self, name: str
	) -> tuple[str, ContainerHealthInfo, ContainerMetrics, list[str]]:
		raw_inspect = self.engine.inspect_container(name)
		cid = raw_inspect.get("Id", "")[:12]
		state = raw_inspect.get("State", {})
		health_obj = state.get("Health") or {}

		status = state.get("Status", "unknown").lower()
		health = health_obj.get("Status", "none").lower()

		app_probe = "skipped"
		if status == "running" and self.config.enable_app_probes:
			app_probe = "healthy" if self._run_app_probe(name) else "failed"

		health_info = ContainerHealthInfo(
			status=status,
			health=health,
			app_probe_status=app_probe,
			oom_killed=bool(state.get("OOMKilled", False)),
			exit_code=int(state.get("ExitCode", 0)),
			restart_count=int(raw_inspect.get("RestartCount", 0)),
			started_at=state.get("StartedAt", ""),
		)

		metrics = ContainerMetrics()
		alerts: list[str] = []

		if status == "running":
			raw_stats = self.engine.get_container_stats(name)
			metrics = self._parse_stats(raw_stats)

			if metrics.cpu_percent >= self.config.cpu_threshold_percent:
				alerts.append(
					f"High CPU utilization: {metrics.cpu_percent:.1f}% "
					f"(Threshold: {self.config.cpu_threshold_percent}%)"
				)
			if metrics.memory_percent >= self.config.memory_threshold_percent:
				alerts.append(
					f"High Memory utilization: {metrics.memory_percent:.1f}% "
					f"(Threshold: {self.config.memory_threshold_percent}%)"
				)

		if health_info.oom_killed:
			alerts.append("Container previously terminated by Linux OOM Killer (OOMKilled=true)")
		if app_probe == "failed":
			alerts.append("Application-level liveness probe failed while container is 'running'")

		return cid, health_info, metrics, alerts

	def _run_app_probe(self, name: str) -> bool:
		if "redis" in name:
			return self.engine.exec_probe(name, ["redis-cli", "ping"])
		if "mariadb" in name or "mysql" in name:
			return (
				self.engine.exec_probe(name, ["mariadb-admin", "ping", "-uroot", "-p123"])
				or self.engine.exec_probe(name, ["mariadb-admin", "ping"])
				or self.engine.exec_probe(name, ["mysqladmin", "ping"])
			)
		if "frappe" in name:
			return self.engine.exec_probe(
				name,
				[
					"python3",
					"-c",
					"import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/api/method/ping', timeout=3)",
				],
			)
		return True

	def _parse_stats(self, raw_stats: dict[str, Any]) -> ContainerMetrics:
		if raw_stats.get("_cli_format"):
			# Fallback CLI parser if Unix socket was unavailable
			data = raw_stats["raw"]
			cpu_str = data.get("CPUPerc", "0%").rstrip("%")
			mem_str = data.get("MemPerc", "0%").rstrip("%")
			pids_str = data.get("PIDs", "0")
			return ContainerMetrics(
				cpu_percent=round(float(cpu_str or 0.0), 2),
				memory_percent=round(float(mem_str or 0.0), 2),
				pids=int(pids_str if pids_str.isdigit() else 0),
			)

		# Direct Docker Engine Socket JSON calculation (cgroup v1/v2 accurate)
		cpu_stats = raw_stats.get("cpu_stats", {})
		precpu_stats = raw_stats.get("precpu_stats", {})

		cpu_delta = cpu_stats.get("cpu_usage", {}).get("total_usage", 0) - precpu_stats.get(
			"cpu_usage", {}
		).get("total_usage", 0)
		sys_delta = cpu_stats.get("system_cpu_usage", 0) - precpu_stats.get("system_cpu_usage", 0)
		online_cpus = cpu_stats.get("online_cpus") or len(
			cpu_stats.get("cpu_usage", {}).get("percpu_usage") or [1]
		)

		cpu_percent = 0.0
		if sys_delta > 0 and cpu_delta > 0:
			cpu_percent = (cpu_delta / sys_delta) * online_cpus * 100.0

		mem_stats = raw_stats.get("memory_stats", {})
		usage = int(mem_stats.get("usage", 0))
		inactive_file = int(mem_stats.get("stats", {}).get("inactive_file", 0))
		actual_used = max(0, usage - inactive_file)
		limit = int(mem_stats.get("limit", 0))
		mem_percent = (actual_used / limit * 100.0) if limit > 0 else 0.0
		pids = int(raw_stats.get("pids_stats", {}).get("current", 0))

		return ContainerMetrics(
			cpu_percent=round(cpu_percent, 2),
			memory_used_bytes=actual_used,
			memory_used_human=format_bytes(actual_used),
			memory_limit_bytes=limit,
			memory_limit_human=format_bytes(limit),
			memory_percent=round(mem_percent, 2),
			pids=pids,
		)
