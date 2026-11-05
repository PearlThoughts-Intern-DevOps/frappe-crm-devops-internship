"""Comprehensive unit test suite for Docker Container Monitoring and Auto-Recovery Tool."""

from __future__ import annotations

import datetime
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

from docker_monitor.monitor import (
	EXIT_DEGRADED,
	EXIT_DOCKER_ERROR,
	EXIT_HEALTHY,
	EXIT_INVALID_CONFIG,
	EXIT_SAFETY_VIOLATION,
	DockerException,
	DockerMonitor,
	main,
	mask_sensitive_data,
	safe_resolve_path,
)


def create_mock_container(
	name: str,
	status: str = "running",
	health_status: str | None = None,
	compose_project: str = "crm",
	restart_count: int = 0,
	exit_code: int | None = 0,
	stats_payload: dict | None = None,
	logs_payload: bytes = b"",
) -> MagicMock:
	"""Helper to generate a mock Docker container with realistic attrs and methods."""
	container = MagicMock()
	container.name = name
	container.id = f"mock_{name}_id_1234567890"
	container.status = status

	state_dict = {
		"Status": status,
		"ExitCode": exit_code,
		"StartedAt": "2026-11-05T07:00:00Z",
		"FinishedAt": "2026-11-05T07:05:00Z" if status != "running" else "",
	}
	if health_status is not None:
		state_dict["Health"] = {"Status": health_status}

	container.attrs = {
		"Created": "2026-11-05T06:00:00Z",
		"RestartCount": restart_count,
		"State": state_dict,
		"Config": {
			"Image": f"frappe/{name}:latest",
			"Labels": {
				"com.docker.compose.project": compose_project,
				"com.docker.compose.service": name,
			},
		},
	}

	container.stats.return_value = stats_payload or {
		"cpu_stats": {
			"cpu_usage": {"total_usage": 1050000000},
			"system_cpu_usage": 10000000000,
			"online_cpus": 1,
		},
		"precpu_stats": {
			"cpu_usage": {"total_usage": 1000000000},
			"system_cpu_usage": 9000000000,
			"online_cpus": 1,
		},
		"memory_stats": {
			"usage": 200000000,
			"limit": 1000000000,
			"stats": {"inactive_file": 50000000},
		},
	}
	container.logs.return_value = logs_payload
	return container


class TestDockerMonitor(unittest.TestCase):
	"""Test suite validating monitoring, telemetry, log analysis, and safe auto-recovery."""

	def setUp(self) -> None:
		self.mock_client = MagicMock()
		self.temp_dir = tempfile.TemporaryDirectory()
		self.report_dir = Path(self.temp_dir.name)
		self.config = {
			"compose_project": "crm",
			"report_dir": str(self.report_dir),
			"auto_recovery_enabled": False,
			"allowed_recovery_containers": ["crm-monitor-test-service"],
			"max_recovery_attempts": 2,
			"recovery_cooldown_seconds": 10,
		}
		self.monitor = DockerMonitor(config=self.config, client=self.mock_client)

	def tearDown(self) -> None:
		self.temp_dir.cleanup()

	def test_mask_sensitive_data(self) -> None:
		"""Verify credentials and secrets are masked from log text."""
		raw = "Database connection: password=supersecret123, token: abc-xyz-987"
		masked = mask_sensitive_data(raw)
		self.assertNotIn("supersecret123", masked)
		self.assertNotIn("abc-xyz-987", masked)
		self.assertIn("password=******", masked)
		self.assertIn("token=******", masked)

		cmd = "bench restore --mariadb-root-password secretpwd dump.sql"
		self.assertIn("--mariadb-root-password=******", mask_sensitive_data(cmd))

	def test_safe_resolve_path_prevents_directory_traversal(self) -> None:
		"""Verify path traversal sequences are rejected."""
		with self.assertRaises(ValueError):
			safe_resolve_path(self.report_dir, "../../etc/passwd")

		valid = safe_resolve_path(self.report_dir, "report.json")
		self.assertTrue(str(valid).startswith(str(self.report_dir.resolve())))

	def test_docker_daemon_connection_failure(self) -> None:
		"""Verify Docker connection failure raises DockerException gracefully."""
		monitor_no_client = DockerMonitor(config=self.config)
		with patch("docker_monitor.monitor.docker.from_env") as mock_from_env:
			mock_from_env.side_effect = Exception("Docker daemon is not running")
			with self.assertRaises(DockerException):
				monitor_no_client.get_client()

	def test_container_discovery_by_compose_project(self) -> None:
		"""Verify containers are filtered by Compose project label."""
		c1 = create_mock_container("crm-frappe-1", compose_project="crm")
		c2 = create_mock_container("crm-mariadb-1", compose_project="crm")
		c3 = create_mock_container("other-nginx-1", compose_project="other_app")

		self.mock_client.containers.list.return_value = [c1, c2, c3]
		discovered = self.monitor.discover_containers()

		self.assertEqual(len(discovered), 2)
		names = [c.name for c in discovered]
		self.assertIn("crm-frappe-1", names)
		self.assertIn("crm-mariadb-1", names)
		self.assertNotIn("other-nginx-1", names)

	def test_container_discovery_by_explicit_names(self) -> None:
		"""Verify container discovery by explicit configured list."""
		c1 = create_mock_container("test-container-a", compose_project="any")
		c2 = create_mock_container("test-container-b", compose_project="any")
		self.mock_client.containers.list.return_value = [c1, c2]

		monitor_explicit = DockerMonitor(
			config={"container_names": ["test-container-a"]},
			client=self.mock_client,
		)
		discovered = monitor_explicit.discover_containers()
		self.assertEqual(len(discovered), 1)
		self.assertEqual(discovered[0].name, "test-container-a")

	def test_cpu_calculation_accuracy(self) -> None:
		"""Verify correct CPU percentage calculation from delta and online CPUs."""
		stats = {
			"cpu_stats": {
				"cpu_usage": {"total_usage": 1500000000},
				"system_cpu_usage": 5000000000,
				"online_cpus": 2,
			},
			"precpu_stats": {
				"cpu_usage": {"total_usage": 1000000000},
				"system_cpu_usage": 4000000000,
				"online_cpus": 2,
			},
		}
		# cpu_delta = 500,000,000, system_delta = 1,000,000,000. (0.5) * 2 * 100 = 100.0%
		cpu_percent = self.monitor.calculate_cpu_percent(stats)
		self.assertEqual(cpu_percent, 100.0)

	def test_cpu_calculation_zero_division_safety(self) -> None:
		"""Verify calculation handles zero delta safely without throwing."""
		stats = {
			"cpu_stats": {"cpu_usage": {"total_usage": 1000}, "system_cpu_usage": 2000},
			"precpu_stats": {"cpu_usage": {"total_usage": 1000}, "system_cpu_usage": 2000},
		}
		cpu_percent = self.monitor.calculate_cpu_percent(stats)
		self.assertEqual(cpu_percent, 0.0)

	def test_memory_calculation_cgroups_cache_adjustment(self) -> None:
		"""Verify inactive_file / cache deduction in memory percentage."""
		stats = {
			"memory_stats": {
				"usage": 300000000,
				"limit": 1000000000,
				"stats": {"inactive_file": 100000000},
			}
		}
		used, limit, percent = self.monitor.calculate_memory_metrics(stats)
		self.assertEqual(used, 200000000)
		self.assertEqual(limit, 1000000000)
		self.assertEqual(percent, 20.0)

	def test_memory_calculation_missing_limit(self) -> None:
		"""Verify memory calculation returns None when limit is zero or missing."""
		stats = {"memory_stats": {"usage": 100, "limit": 0}}
		used, limit, percent = self.monitor.calculate_memory_metrics(stats)
		self.assertIsNone(used)
		self.assertIsNone(limit)
		self.assertIsNone(percent)

	def test_inspect_running_healthy_container(self) -> None:
		"""Verify inspection of a running container with healthy Docker status."""
		c = create_mock_container("crm-frappe-1", status="running", health_status="healthy")
		data = self.monitor.inspect_container(c)

		self.assertEqual(data["name"], "crm-frappe-1")
		self.assertEqual(data["status"], "running")
		self.assertEqual(data["health_status"], "healthy")
		self.assertIsNotNone(data["cpu_percent"])
		self.assertIsNotNone(data["memory_percent"])
		self.assertEqual(len(data["issues"]), 0)

	def test_inspect_stopped_container_null_metrics(self) -> None:
		"""Verify stopped container reports null metrics and appropriate issue note."""
		c = create_mock_container("crm-mariadb-1", status="exited", exit_code=1)
		data = self.monitor.inspect_container(c)

		self.assertEqual(data["status"], "exited")
		self.assertEqual(data["health_status"], "not_configured")
		self.assertIsNone(data["cpu_percent"])
		self.assertIsNone(data["memory_percent"])
		self.assertTrue(any("not running" in issue for issue in data["issues"]))

	def test_inspect_container_without_healthcheck(self) -> None:
		"""Verify containers without health checks report health_status as 'not_configured'."""
		c = create_mock_container("crm-redis-1", status="running", health_status=None)
		data = self.monitor.inspect_container(c)

		self.assertEqual(data["health_status"], "not_configured")

	def test_inspect_unhealthy_container_reports_issue(self) -> None:
		"""Verify unhealthy Docker status triggers issue detection."""
		c = create_mock_container("crm-frappe-1", status="running", health_status="unhealthy")
		data = self.monitor.inspect_container(c)

		self.assertEqual(data["health_status"], "unhealthy")
		self.assertTrue(any("unhealthy" in issue.lower() for issue in data["issues"]))

	def test_log_analysis_error_and_warning_detection(self) -> None:
		"""Verify log keyword scanning counts errors and warnings with sanitized samples."""
		log_content = (
			b"2026-11-05T07:00:00Z INFO Server started on port 8000\n"
			b"2026-11-05T07:01:00Z WARNING Redis cache latency high\n"
			b"2026-11-05T07:02:00Z ERROR Database connection failed with password=db_secret123\n"
			b"2026-11-05T07:03:00Z CRITICAL Traceback (most recent call last):\n"
		)
		c = create_mock_container("crm-frappe-1", logs_payload=log_content)
		analysis = self.monitor.analyze_container_logs(c)

		self.assertEqual(analysis["warning_count"], 1)
		self.assertEqual(analysis["error_count"], 2)
		self.assertTrue(len(analysis["sample_errors"]) > 0)
		self.assertNotIn("db_secret123", str(analysis["sample_errors"]))
		self.assertIn("password=******", str(analysis["sample_errors"]))

	def test_auto_recovery_disabled_by_default(self) -> None:
		"""Verify auto-recovery does not execute when disabled."""
		c_stopped = create_mock_container("crm-monitor-test-service", status="exited", exit_code=1)
		self.mock_client.containers.list.return_value = [c_stopped]

		exit_code, report = self.monitor.run_monitoring_cycle(trigger_recovery=False)
		self.assertEqual(exit_code, EXIT_DEGRADED)
		self.assertFalse(report["auto_recovery"]["enabled"])
		self.assertEqual(len(report["auto_recovery"]["actions_taken"]), 0)
		c_stopped.restart.assert_not_called()

	def test_auto_recovery_refuses_original_crm_containers(self) -> None:
		"""STRICT SAFETY CHECK: Auto-recovery must never restart original CRM containers."""
		c_original = create_mock_container("crm-frappe-1", status="exited", compose_project="crm")
		self.mock_client.containers.list.return_value = [c_original]

		exit_code, report = self.monitor.run_monitoring_cycle(trigger_recovery=True)
		self.assertEqual(exit_code, EXIT_SAFETY_VIOLATION)
		actions = report["auto_recovery"]["actions_taken"]
		self.assertEqual(len(actions), 1)
		self.assertEqual(actions[0]["status"], "SAFETY_VIOLATION")
		c_original.restart.assert_not_called()

	def test_auto_recovery_refuses_non_allowlisted_containers(self) -> None:
		"""STRICT SAFETY CHECK: Auto-recovery must reject containers not in allowlist."""
		c_random = create_mock_container("random-test-container", status="exited", compose_project="testing")
		self.mock_client.containers.list.return_value = [c_random]

		monitor_isolated = DockerMonitor(
			config={
				"container_names": ["random-test-container"],
				"auto_recovery_enabled": True,
				"allowed_recovery_containers": ["crm-monitor-test-service"],
			},
			client=self.mock_client,
		)
		exit_code, report = monitor_isolated.run_monitoring_cycle()
		self.assertEqual(exit_code, EXIT_DEGRADED)
		actions = report["auto_recovery"]["actions_taken"]
		self.assertEqual(actions[0]["status"], "NOT_ALLOWLISTED")
		c_random.restart.assert_not_called()

	def test_auto_recovery_restarts_allowlisted_test_container(self) -> None:
		"""Verify auto-recovery restarts an explicitly allowlisted test container."""
		c_test = create_mock_container(
			"crm-monitor-test-service", status="exited", compose_project="test-proj"
		)
		self.mock_client.containers.list.return_value = [c_test]

		monitor_test = DockerMonitor(
			config={
				"container_names": ["crm-monitor-test-service"],
				"auto_recovery_enabled": True,
				"allowed_recovery_containers": ["crm-monitor-test-service"],
			},
			client=self.mock_client,
		)
		exit_code, report = monitor_test.run_monitoring_cycle()
		self.assertEqual(exit_code, EXIT_DEGRADED)
		actions = report["auto_recovery"]["actions_taken"]
		self.assertEqual(len(actions), 1)
		self.assertEqual(actions[0]["status"], "SUCCESS")
		c_test.restart.assert_called_once_with(timeout=10)

	def test_auto_recovery_rate_limit_and_cooldown(self) -> None:
		"""Verify retry count and cooldown prevent rapid restart loops."""
		c_test = create_mock_container(
			"crm-monitor-test-service", status="exited", compose_project="test-proj"
		)
		monitor_test = DockerMonitor(
			config={
				"container_names": ["crm-monitor-test-service"],
				"auto_recovery_enabled": True,
				"allowed_recovery_containers": ["crm-monitor-test-service"],
				"max_recovery_attempts": 2,
				"recovery_cooldown_seconds": 60,
			},
			client=self.mock_client,
		)

		c_info = monitor_test.inspect_container(c_test)

		# Attempt 1 -> Success
		res1 = monitor_test.attempt_recovery(c_info, c_test)
		self.assertEqual(res1["status"], "SUCCESS")

		# Attempt 2 immediate -> Cooldown active
		res2 = monitor_test.attempt_recovery(c_info, c_test)
		self.assertEqual(res2["status"], "COOLDOWN_ACTIVE")

		# Fast forward past cooldown
		monitor_test._recovery_history["crm-monitor-test-service"] = [
			datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(seconds=65)
		]
		res3 = monitor_test.attempt_recovery(c_info, c_test)
		self.assertEqual(res3["status"], "SUCCESS")

		# Attempt 4 after reaching max attempts (2)
		res4 = monitor_test.attempt_recovery(c_info, c_test)
		self.assertEqual(res4["status"], "MAX_ATTEMPTS_EXCEEDED")

	def test_save_report_generates_valid_json_file(self) -> None:
		"""Verify report is serialized to valid JSON on disk atomically."""
		report_data = {
			"report_version": "1.0",
			"generated_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
			"overall_status": "healthy",
			"monitoring_summary": {"total_containers": 1, "running": 1},
			"containers": [],
		}
		path = self.monitor.save_report(report_data, output_dir=self.report_dir)
		self.assertTrue(path.exists())
		loaded = json.loads(path.read_text(encoding="utf-8"))
		self.assertEqual(loaded["overall_status"], "healthy")

	def test_high_cpu_threshold_triggers_issue(self) -> None:
		"""Verify high CPU utilization triggers an issue warning."""
		high_cpu_stats = {
			"cpu_stats": {
				"cpu_usage": {"total_usage": 9000000000},
				"system_cpu_usage": 10000000000,
				"online_cpus": 1,
			},
			"precpu_stats": {
				"cpu_usage": {"total_usage": 8000000000},
				"system_cpu_usage": 9000000000,
				"online_cpus": 1,
			},
			"memory_stats": {"usage": 100, "limit": 1000},
		}
		c = create_mock_container("crm-frappe-1", status="running", stats_payload=high_cpu_stats)
		data = self.monitor.inspect_container(c)
		self.assertTrue(any("High CPU utilization" in issue for issue in data["issues"]))

	def test_high_memory_threshold_triggers_issue(self) -> None:
		"""Verify high memory utilization triggers an issue warning."""
		high_mem_stats = {
			"cpu_stats": {"cpu_usage": {"total_usage": 1000}, "system_cpu_usage": 2000, "online_cpus": 1},
			"precpu_stats": {"cpu_usage": {"total_usage": 1000}, "system_cpu_usage": 2000, "online_cpus": 1},
			"memory_stats": {
				"usage": 950000000,
				"limit": 1000000000,
				"stats": {"inactive_file": 10000000},
			},
		}
		c = create_mock_container("crm-frappe-1", status="running", stats_payload=high_mem_stats)
		data = self.monitor.inspect_container(c)
		self.assertTrue(any("High Memory utilization" in issue for issue in data["issues"]))

	def test_main_cli_successful_monitor_and_report(self) -> None:
		"""Verify CLI execution runs monitoring cycle, displays summary, and writes report."""
		c = create_mock_container("crm-frappe-1", status="running", health_status="healthy")
		with patch("docker_monitor.monitor.docker.from_env") as mock_from_env:
			mock_client = MagicMock()
			mock_client.containers.list.return_value = [c]
			mock_from_env.return_value = mock_client
			exit_code = main(["monitor", "--report", "--report-dir", str(self.report_dir)])
			self.assertEqual(exit_code, EXIT_HEALTHY)
			report_files = list(self.report_dir.glob("docker_health_report_*.json"))
			self.assertEqual(len(report_files), 1)

	def test_main_cli_invalid_config_handling(self) -> None:
		"""Verify CLI handles missing config file gracefully."""
		exit_code = main(["monitor", "--config", "non_existent_config_file.json"])
		self.assertEqual(exit_code, EXIT_INVALID_CONFIG)


if __name__ == "__main__":
	unittest.main()
