import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock

from DockerMonitor.analyzer import LogAnalyzer
from DockerMonitor.collector import MetricsCollector
from DockerMonitor.config import MonitorConfig
from DockerMonitor.models import (
	ContainerHealthInfo,
	ContainerMetrics,
	ContainerStatusReport,
	LogErrorSummary,
)
from DockerMonitor.recovery import AutoRecoveryEngine
from DockerMonitor.reporter import HealthReporter
from DockerMonitor.state import StateManager


class TestDockerMonitor(unittest.TestCase):
	def setUp(self) -> None:
		self.tmp_dir = tempfile.TemporaryDirectory()
		self.config = MonitorConfig(base_dir=Path(self.tmp_dir.name), auto_restart_enabled=True)

	def tearDown(self) -> None:
		self.tmp_dir.cleanup()

	def test_traceback_folding_counts_as_single_error(self) -> None:
		sample_log = """
        2026-11-05 10:00:01 INFO Starting worker
        Traceback (most recent call last):
          File "/home/frappe/app.py", line 10, in <module>
            connect_db()
         pymysql.err.OperationalError: (2003, "Can't connect to MySQL server")
        2026-11-05 10:00:05 WARNING Deadlock found when trying to get lock
        """
		analyzer = LogAnalyzer()
		res = analyzer.analyze(sample_log)
		self.assertEqual(res.errors, 1)
		self.assertEqual(res.critical_errors, 0)
		self.assertEqual(res.warnings, 1)

	def test_cgroup_stats_calculation(self) -> None:
		engine = MagicMock()
		collector = MetricsCollector(engine, self.config)
		raw_socket_stats = {
			"cpu_stats": {
				"cpu_usage": {"total_usage": 200_000_000},
				"system_cpu_usage": 2_000_000_000,
				"online_cpus": 4,
			},
			"precpu_stats": {"cpu_usage": {"total_usage": 100_000_000}, "system_cpu_usage": 1_000_000_000},
			"memory_stats": {
				"usage": 600 * 1024 * 1024,
				"limit": 1200 * 1024 * 1024,
				"stats": {"inactive_file": 100 * 1024 * 1024},
			},
			"pids_stats": {"current": 42},
		}
		metrics = collector._parse_stats(raw_socket_stats)
		self.assertAlmostEqual(metrics.cpu_percent, 40.0)
		self.assertAlmostEqual(metrics.memory_percent, 41.67, places=2)
		self.assertEqual(metrics.pids, 42)

	def test_circuit_breaker_trips_after_max_attempts(self) -> None:
		engine = MagicMock()
		engine.restart_container.return_value = True
		engine.inspect_container.return_value = {"State": {"Status": "exited"}}
		state = StateManager(self.config.state_file)
		self.config.restart_cooldown_seconds = 0
		self.config.verify_wait_seconds = 0

		recovery = AutoRecoveryEngine(engine, state, self.config, MagicMock())
		dummy_report = ContainerStatusReport(
			name="crm-redis-1",
			id="123456",
			state=ContainerHealthInfo(status="exited"),
			metrics=ContainerMetrics(),
			threshold_alerts=[],
			log_analysis=LogErrorSummary(),
		)

		for _ in range(3):
			recovery.evaluate_and_recover([dummy_report])

		st = state.get_container_state("crm-redis-1")
		self.assertTrue(st["circuit_breaker_tripped"])

		# 4th call should be blocked by circuit breaker
		actions = recovery.evaluate_and_recover([dummy_report])
		self.assertEqual(actions[0].action, "CIRCUIT_OPEN")

	def test_topological_recovery_order(self) -> None:
		engine = MagicMock()
		state = StateManager(self.config.state_file)
		recovery = AutoRecoveryEngine(engine, state, self.config, MagicMock())

		rep_frappe = ContainerStatusReport(
			name="crm-frappe-1",
			id="f1",
			state=ContainerHealthInfo(status="exited"),
			metrics=ContainerMetrics(),
			threshold_alerts=[],
			log_analysis=LogErrorSummary(),
		)
		rep_mariadb = ContainerStatusReport(
			name="crm-mariadb-1",
			id="m1",
			state=ContainerHealthInfo(status="exited"),
			metrics=ContainerMetrics(),
			threshold_alerts=[],
			log_analysis=LogErrorSummary(),
		)
		rep_redis = ContainerStatusReport(
			name="crm-redis-1",
			id="r1",
			state=ContainerHealthInfo(status="exited"),
			metrics=ContainerMetrics(),
			threshold_alerts=[],
			log_analysis=LogErrorSummary(),
		)

		# Sort order should place MariaDB and Redis (Tier 1) before Frappe (Tier 2)
		sorted_reports = sorted([rep_frappe, rep_mariadb, rep_redis], key=recovery._startup_priority)
		self.assertEqual(sorted_reports[2].name, "crm-frappe-1")
		self.assertIn(sorted_reports[0].name, ["crm-mariadb-1", "crm-redis-1"])
		self.assertIn(sorted_reports[1].name, ["crm-mariadb-1", "crm-redis-1"])

	def test_dry_run_does_not_mutate_containers(self) -> None:
		engine = MagicMock()
		state = StateManager(self.config.state_file)
		self.config.dry_run = True
		recovery = AutoRecoveryEngine(engine, state, self.config, MagicMock())

		dummy_report = ContainerStatusReport(
			name="crm-redis-1",
			id="123",
			state=ContainerHealthInfo(status="exited"),
			metrics=ContainerMetrics(),
			threshold_alerts=[],
			log_analysis=LogErrorSummary(),
		)
		actions = recovery.evaluate_and_recover([dummy_report])
		self.assertEqual(len(actions), 1)
		self.assertEqual(actions[0].action, "DRY_RUN_RESTART")
		engine.restart_container.assert_not_called()

	def test_json_report_generation_and_rotation(self) -> None:
		reporter = HealthReporter(self.config)
		self.config.max_reports_kept = 2

		dummy_report = ContainerStatusReport(
			name="crm-redis-1",
			id="123",
			state=ContainerHealthInfo(status="running"),
			metrics=ContainerMetrics(cpu_percent=1.5, memory_percent=10.0),
			threshold_alerts=[],
			log_analysis=LogErrorSummary(),
		)
		report = reporter.build_report([dummy_report], [])
		self.assertEqual(report.cluster_status, "HEALTHY")

		path1 = reporter.save_json_report(report)
		self.assertTrue(path1.exists())
		self.assertTrue((self.config.reports_dir / "latest_health_report.json").exists())

		# Validate JSON content
		data = json.loads(path1.read_text(encoding="utf-8"))
		self.assertEqual(data["cluster_status"], "HEALTHY")
		self.assertEqual(data["summary"]["running"], 1)


if __name__ == "__main__":
	unittest.main()
