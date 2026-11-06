from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class MonitorConfig:
	project_name: str = "crm"
	target_containers: list[str] = field(
		default_factory=lambda: ["crm-mariadb-1", "crm-redis-1", "crm-frappe-1"]
	)
	socket_path: str = "/var/run/docker.sock"
	cpu_threshold_percent: float = 85.0
	memory_threshold_percent: float = 85.0
	log_tail_lines: int = 250
	auto_restart_enabled: bool = False
	max_restart_attempts: int = 3
	restart_cooldown_seconds: int = 60
	stability_reset_seconds: int = 600  # Reset retry counter after 10m healthy
	verify_wait_seconds: int = 5
	max_reports_kept: int = 100
	base_dir: Path = field(default_factory=lambda: Path(__file__).resolve().parent.parent)
	reports_dir: Path = field(init=False)
	logs_dir: Path = field(init=False)
	state_file: Path = field(init=False)
	dry_run: bool = False
	enable_app_probes: bool = True

	def __post_init__(self) -> None:
		self.reports_dir = self.base_dir / "reports"
		self.logs_dir = self.base_dir / "logs"
		self.state_file = self.base_dir / "state" / "monitor_state.json"
		self.reports_dir.mkdir(parents=True, exist_ok=True)
		self.logs_dir.mkdir(parents=True, exist_ok=True)
		self.state_file.parent.mkdir(parents=True, exist_ok=True)
