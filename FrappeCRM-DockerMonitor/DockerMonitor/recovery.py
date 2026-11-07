import logging
import time
from datetime import datetime, timezone

from .config import MonitorConfig
from .engine import DockerEngineClient
from .exceptions import RecoveryExecutionError
from .models import ContainerStatusReport, RecoveryAction
from .state import StateManager


class AutoRecoveryEngine:
	"""Executes guarded, dependency-ordered container auto-recovery with persistent circuit breaking."""

	def __init__(
		self,
		engine: DockerEngineClient,
		state: StateManager,
		config: MonitorConfig,
		logger: logging.Logger,
	) -> None:
		self.engine = engine
		self.state = state
		self.config = config
		self.logger = logger

	@staticmethod
	def _startup_priority(report: ContainerStatusReport) -> int:
		# Tier 1: MariaDB & Redis wake up before Tier 2: Frappe Web/Workers
		if "mariadb" in report.name or "redis" in report.name:
			return 0
		return 1

	def evaluate_and_recover(self, reports: list[ContainerStatusReport]) -> list[RecoveryAction]:
		actions: list[RecoveryAction] = []
		ordered_reports = sorted(reports, key=self._startup_priority)

		for rep in ordered_reports:
			needs_recovery = (
				rep.state.status != "running"
				or rep.state.health == "unhealthy"
				or rep.state.app_probe_status == "failed"
			)

			if not needs_recovery:
				self.state.record_healthy(rep.name, self.config.stability_reset_seconds)
				continue

			st = self.state.get_container_state(rep.name)
			now_iso = datetime.now(timezone.utc).isoformat()

			if not self.config.auto_restart_enabled:
				self.logger.warning(
					f"[{rep.name}] Unhealthy/Stopped (status={rep.state.status}, probe={rep.state.app_probe_status}). "
					"Auto-restart is disabled. Pass --auto-restart to heal."
				)
				continue

			if st["circuit_breaker_tripped"]:
				msg = f"Circuit breaker tripped after {st['restart_attempts']} failed attempts. Manual intervention required."
				self.logger.critical(f"[{rep.name}] {msg}")
				actions.append(
					RecoveryAction(
						now_iso,
						rep.name,
						rep.state.status,
						"CIRCUIT_OPEN",
						False,
						st["restart_attempts"],
						0.0,
						msg,
					)
				)
				continue

			elapsed = time.time() - st["last_restart_ts"]
			if elapsed < self.config.restart_cooldown_seconds:
				rem = int(self.config.restart_cooldown_seconds - elapsed)
				msg = f"In cooldown window ({rem}s remaining). Skipping restart."
				self.logger.warning(f"[{rep.name}] {msg}")
				actions.append(
					RecoveryAction(
						now_iso,
						rep.name,
						rep.state.status,
						"COOLDOWN_SKIP",
						False,
						st["restart_attempts"],
						0.0,
						msg,
					)
				)
				continue

			if self.config.dry_run:
				msg = f"[DRY-RUN] Would restart container '{rep.name}' (attempt {st['restart_attempts'] + 1}/{self.config.max_restart_attempts})."
				self.logger.info(msg)
				actions.append(
					RecoveryAction(
						now_iso,
						rep.name,
						rep.state.status,
						"DRY_RUN_RESTART",
						True,
						st["restart_attempts"] + 1,
						0.0,
						msg,
					)
				)
				continue

			# Execute actual restart
			start_t = time.monotonic()
			attempt_num = self.state.record_restart_attempt(rep.name, self.config.max_restart_attempts)
			self.logger.warning(
				f"[{rep.name}] Attempting auto-restart ({attempt_num}/{self.config.max_restart_attempts})..."
			)
			try:
				self.engine.restart_container(rep.name)
				time.sleep(self.config.verify_wait_seconds)
				post_inspect = self.engine.inspect_container(rep.name)
				post_status = post_inspect.get("State", {}).get("Status", "unknown").lower()
				duration = round(time.monotonic() - start_t, 2)

				if post_status == "running":
					rep.state.status = "running"
					msg = f"Container restarted and verified 'running' after {duration}s."
					self.logger.info(f"[{rep.name}] {msg}")
					actions.append(
						RecoveryAction(
							now_iso,
							rep.name,
							"stopped/unhealthy",
							"RESTART",
							True,
							attempt_num,
							duration,
							msg,
						)
					)
				else:
					msg = f"Container restarted but transitioned to '{post_status}'."
					self.logger.error(f"[{rep.name}] {msg}")
					actions.append(
						RecoveryAction(
							now_iso,
							rep.name,
							"stopped/unhealthy",
							"RESTART",
							False,
							attempt_num,
							duration,
							msg,
						)
					)
			except RecoveryExecutionError as exc:
				duration = round(time.monotonic() - start_t, 2)
				self.logger.error(f"[{rep.name}] Restart failed: {exc}")
				actions.append(
					RecoveryAction(
						now_iso, rep.name, rep.state.status, "RESTART", False, attempt_num, duration, str(exc)
					)
				)

		return actions
