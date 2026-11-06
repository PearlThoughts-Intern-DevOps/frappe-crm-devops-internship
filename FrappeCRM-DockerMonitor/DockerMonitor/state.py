import json
import time
from pathlib import Path
from typing import Any


class StateManager:
	"""Persists retry counters, cooldown timestamps, and log cursors across cron runs."""

	def __init__(self, state_file: Path) -> None:
		self.state_file = state_file
		self.data: dict[str, Any] = self._load()

	def _load(self) -> dict[str, Any]:
		if self.state_file.exists():
			try:
				return json.loads(self.state_file.read_text(encoding="utf-8"))
			except (json.JSONDecodeError, OSError):
				pass
		return {"containers": {}}

	def save(self) -> None:
		temp_file = self.state_file.with_suffix(".tmp")
		temp_file.write_text(json.dumps(self.data, indent=2), encoding="utf-8")
		temp_file.replace(self.state_file)

	def get_container_state(self, name: str) -> dict[str, Any]:
		containers = self.data.setdefault("containers", {})
		return containers.setdefault(
			name,
			{
				"restart_attempts": 0,
				"last_restart_ts": 0.0,
				"circuit_breaker_tripped": False,
				"healthy_since_ts": 0.0,
				"last_log_cursor_ts": int(time.time()) - 300,
			},
		)

	def record_healthy(self, name: str, stability_reset_seconds: int) -> None:
		st = self.get_container_state(name)
		now = time.time()
		if st["healthy_since_ts"] == 0.0:
			st["healthy_since_ts"] = now
		elif (now - st["healthy_since_ts"]) >= stability_reset_seconds:
			st["restart_attempts"] = 0
			st["circuit_breaker_tripped"] = False
		self.save()

	def record_restart_attempt(self, name: str, max_attempts: int) -> int:
		st = self.get_container_state(name)
		st["restart_attempts"] += 1
		st["last_restart_ts"] = time.time()
		st["healthy_since_ts"] = 0.0
		if st["restart_attempts"] >= max_attempts:
			st["circuit_breaker_tripped"] = True
		self.save()
		return st["restart_attempts"]

	def update_log_cursor(self, name: str, timestamp: int) -> None:
		st = self.get_container_state(name)
		st["last_log_cursor_ts"] = timestamp
		self.save()
