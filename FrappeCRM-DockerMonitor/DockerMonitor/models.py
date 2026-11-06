from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass
class ContainerMetrics:
	cpu_percent: float = 0.0
	memory_used_bytes: int = 0
	memory_used_human: str = "0.00 MiB"
	memory_limit_bytes: int = 0
	memory_limit_human: str = "0.00 GiB"
	memory_percent: float = 0.0
	pids: int = 0


@dataclass
class ContainerHealthInfo:
	status: str = "unknown"  # running, exited, restarting, dead
	health: str = "none"  # healthy, unhealthy, starting, none
	app_probe_status: str = "skipped"  # healthy, failed, skipped
	oom_killed: bool = False
	exit_code: int = 0
	restart_count: int = 0
	started_at: str = ""


@dataclass
class LogErrorSummary:
	lines_scanned: int = 0
	critical_errors: int = 0
	errors: int = 0
	warnings: int = 0
	detected_issues: list[dict[str, Any]] = field(default_factory=list)


@dataclass
class RecoveryAction:
	timestamp: str
	container: str
	previous_status: str
	action: str
	success: bool
	attempt_number: int
	duration_seconds: float
	message: str


@dataclass
class ContainerStatusReport:
	name: str
	id: str
	state: ContainerHealthInfo
	metrics: ContainerMetrics
	threshold_alerts: list[str]
	log_analysis: LogErrorSummary


@dataclass
class SystemHealthReport:
	timestamp: str
	cluster_status: str  # HEALTHY, DEGRADED, CRITICAL
	summary: dict[str, int]
	containers: list[ContainerStatusReport]
	recovery_actions: list[RecoveryAction] = field(default_factory=list)

	def to_dict(self) -> dict[str, Any]:
		return asdict(self)
