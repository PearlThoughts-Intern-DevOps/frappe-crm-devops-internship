#!/usr/bin/env python3
"""
Unit Tests for Frappe CRM Docker Monitoring & Auto-Recovery Tool
================================================================
Comprehensive unit test suite verifying utility parsing, log pattern analysis,
telemetry evaluation, auto-recovery decision logic, report serialization,
and exception handling without requiring live Docker daemon or root privileges.

Author: DevOps Engineering Team
License: MIT
"""

import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import MagicMock, patch

# Ensure scripts directory is in sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent))

from frappe_docker_monitor import (
    format_size,
    parse_size_string,
    parse_percentage_string,
    calculate_uptime,
    LogAnalyzer,
    HealthEvaluator,
    AutoRecoveryManager,
    ReportGenerator,
    ContainerStats,
    LogAnalysisResult,
    RecoveryAction,
    SystemHealthReport,
    DockerClient,
    DockerClientError,
    DEFAULT_CPU_THRESHOLD,
    DEFAULT_MEM_THRESHOLD,
)


class TestFormattingAndUtilities(unittest.TestCase):
    """Verifies size, percentage, and uptime string parsing and formatting."""

    def test_format_size(self):
        self.assertEqual(format_size(500), "500.0 B")
        self.assertEqual(format_size(1024), "1.0 KiB")
        self.assertEqual(format_size(1024 * 1024), "1.0 MiB")
        self.assertEqual(format_size(1024 * 1024 * 1024 * 2), "2.0 GiB")
        self.assertEqual(format_size(-10), "0.0 B")

    def test_parse_size_string(self):
        self.assertEqual(parse_size_string("500B"), 500)
        self.assertEqual(parse_size_string("10KiB"), 10 * 1024)
        self.assertEqual(parse_size_string("594.4MiB"), int(594.4 * 1024 * 1024))
        self.assertEqual(parse_size_string("7.446GiB"), int(7.446 * 1024 * 1024 * 1024))
        self.assertEqual(parse_size_string("--"), 0)
        self.assertEqual(parse_size_string(""), 0)

    def test_parse_percentage_string(self):
        self.assertAlmostEqual(parse_percentage_string("16.64%"), 16.64)
        self.assertAlmostEqual(parse_percentage_string("0.5%"), 0.5)
        self.assertEqual(parse_percentage_string("--"), 0.0)
        self.assertEqual(parse_percentage_string("invalid"), 0.0)

    def test_calculate_uptime(self):
        # Past timestamp
        iso_str = "2026-11-03T11:39:14.300210413Z"
        res = calculate_uptime(iso_str)
        self.assertTrue(isinstance(res, str))
        self.assertNotEqual(res, "Unknown")

        # Zero / Uninitialized timestamp
        self.assertEqual(calculate_uptime("0001-01-01T00:00:00Z"), "Not Started")
        self.assertEqual(calculate_uptime(""), "Not Started")


class TestLogAnalyzer(unittest.TestCase):
    """Verifies intelligent regex error pattern classification across CRM services."""

    def test_clean_logs(self):
        clean_lines = [
            '172.18.0.1 - - [04/Nov/2026 10:27:09] "GET /api/method/frappe.ping HTTP/1.1" 200 -',
            '172.18.0.1 - - [04/Nov/2026 10:27:09] "POST /api/method/crm.api.doc.get_assigned_users HTTP/1.1" 200 -',
            'DB saved on disk',
        ]
        res = LogAnalyzer.analyze("crm-frappe-1", clean_lines)
        self.assertEqual(res.scanned_lines, 3)
        self.assertEqual(res.error_count, 0)
        self.assertEqual(res.warning_count, 0)
        self.assertEqual(len(res.critical_issues), 0)

    def test_python_traceback_detection(self):
        error_lines = [
            "Traceback (most recent call last):",
            '  File "/home/frappe/frappe-bench/apps/frappe/frappe/app.py", line 69, in application',
            '    response = frappe.api.handle()',
            "OperationalError: (2006, 'MySQL server has gone away')",
        ]
        res = LogAnalyzer.analyze("crm-frappe-1", error_lines)
        self.assertGreaterEqual(res.error_count, 1)
        self.assertIn("PYTHON_EXCEPTION", res.category_counts)
        self.assertTrue(any(issue["severity"] == "CRITICAL" for issue in res.critical_issues))

    def test_mariadb_database_error_detection(self):
        db_lines = [
            "2026-11-03 11:39:18 0 [ERROR] mysqld: Table './crm/tabUser' is marked as crashed",
            "2026-11-03 11:39:18 0 [Warning] Got an error reading communication packets",
        ]
        res = LogAnalyzer.analyze("crm-mariadb-1", db_lines)
        self.assertGreaterEqual(res.error_count, 1)
        self.assertGreaterEqual(res.warning_count, 1)
        self.assertIn("DATABASE_ERROR", res.category_counts)

    def test_redis_oom_detection(self):
        redis_lines = [
            "1:M 05 Nov 2026 10:28:11.117 # OOM command not allowed when used memory > 'maxmemory'",
            "1:M 05 Nov 2026 10:28:11.118 # MISCONF Redis is configured to save RDB snapshots",
        ]
        res = LogAnalyzer.analyze("crm-redis-1", redis_lines)
        self.assertGreaterEqual(res.error_count, 2)
        self.assertIn("REDIS_ERROR", res.category_counts)

    def test_web_server_500_502_detection(self):
        web_lines = [
            '172.18.0.1 - - [04/Nov/2026 10:27:09] "POST /api/method/crm.lead HTTP/1.1" 500 1420',
            '172.18.0.1 - - [04/Nov/2026 10:27:10] "GET /desk HTTP/1.1" 502 520',
            "WORKER TIMEOUT (pid:45)",
        ]
        res = LogAnalyzer.analyze("crm-frappe-1", web_lines)
        self.assertGreaterEqual(res.error_count, 2)
        self.assertIn("WEB_SERVER_ERROR", res.category_counts)


class TestHealthEvaluator(unittest.TestCase):
    """Verifies container status and health classification algorithms."""

    def setUp(self):
        self.evaluator = HealthEvaluator(cpu_threshold=80.0, mem_threshold=80.0)

    def test_healthy_container_evaluation(self):
        inspect_doc = {
            "Id": "ae71acbba1f48ed01f7f4fc435d8d7bbe8d92782b6c23128594378d9253619a2",
            "Config": {"Image": "frappe/bench:latest", "Labels": {"com.docker.compose.service": "frappe"}},
            "State": {"Status": "running", "ExitCode": 0, "OOMKilled": False, "StartedAt": "2026-11-03T11:39:14Z"},
            "NetworkSettings": {"IPAddress": "172.18.0.3", "Ports": {}},
        }
        stats_doc = {
            "CPUPerc": "15.0%",
            "MemPerc": "25.0%",
            "MemUsage": "500MiB / 2GiB",
            "NetIO": "10MB / 5MB",
            "BlockIO": "20MB / 10MB",
            "PIDs": "20",
        }
        c = self.evaluator.build_container_stats("crm-frappe-1", inspect_doc, stats_doc)
        self.assertEqual(c.status, "running")
        self.assertEqual(c.overall_health, "HEALTHY")
        self.assertEqual(len(c.issues), 0)

    def test_stopped_container_evaluation(self):
        inspect_doc = {
            "Id": "1c88372d0255",
            "Config": {"Image": "redis:alpine", "Labels": {"com.docker.compose.service": "redis"}},
            "State": {"Status": "exited", "ExitCode": 137, "OOMKilled": False, "StartedAt": "2026-11-03T11:39:14Z"},
            "NetworkSettings": {"IPAddress": "", "Ports": {}},
        }
        c = self.evaluator.build_container_stats("crm-redis-1", inspect_doc, None)
        self.assertEqual(c.status, "exited")
        self.assertEqual(c.overall_health, "STOPPED")
        self.assertEqual(c.exit_code, 137)
        self.assertTrue(any("stopped" in iss.lower() for iss in c.issues))

    def test_oom_killed_container_evaluation(self):
        inspect_doc = {
            "Id": "a7d101e2412e",
            "Config": {"Image": "mariadb:10.8", "Labels": {"com.docker.compose.service": "mariadb"}},
            "State": {"Status": "exited", "ExitCode": 137, "OOMKilled": True, "StartedAt": "2026-11-03T11:39:14Z"},
            "NetworkSettings": {"IPAddress": "", "Ports": {}},
        }
        c = self.evaluator.build_container_stats("crm-mariadb-1", inspect_doc, None)
        self.assertEqual(c.overall_health, "UNHEALTHY")
        self.assertTrue(any("out-of-memory" in iss.lower() for iss in c.issues))

    def test_high_resource_threshold_degradation(self):
        inspect_doc = {
            "Id": "ae71acbba1f4",
            "Config": {"Image": "frappe/bench:latest", "Labels": {"com.docker.compose.service": "frappe"}},
            "State": {"Status": "running", "ExitCode": 0, "OOMKilled": False, "StartedAt": "2026-11-03T11:39:14Z"},
            "NetworkSettings": {"IPAddress": "172.18.0.3", "Ports": {}},
        }
        # CPU at 95.5%, exceeding 80% threshold
        stats_doc = {
            "CPUPerc": "95.5%",
            "MemPerc": "30.0%",
            "MemUsage": "600MiB / 2GiB",
            "NetIO": "10MB / 5MB",
            "BlockIO": "20MB / 10MB",
            "PIDs": "30",
        }
        c = self.evaluator.build_container_stats("crm-frappe-1", inspect_doc, stats_doc)
        self.assertEqual(c.overall_health, "DEGRADED")
        self.assertTrue(any("high cpu" in iss.lower() for iss in c.issues))


class TestAutoRecoveryManager(unittest.TestCase):
    """Verifies self-healing recovery rules, retry caps, and dry-run execution."""

    def setUp(self):
        self.mock_client = MagicMock(spec=DockerClient)
        self.recovery_mgr = AutoRecoveryManager(
            docker_client=self.mock_client,
            max_retries=3,
            cooldown_sec=0.01,
            dry_run=False,
        )

    def test_should_recover_qualification(self):
        healthy_c = ContainerStats(
            container_id="111", name="crm-redis-1", service="redis", image="redis:alpine",
            status="running", health_status="none", overall_health="HEALTHY",
        )
        qualifies, _ = self.recovery_mgr.should_recover(healthy_c)
        self.assertFalse(qualifies)

        stopped_c = ContainerStats(
            container_id="222", name="crm-mariadb-1", service="mariadb", image="mariadb:10.8",
            status="exited", health_status="none", overall_health="STOPPED",
        )
        qualifies, _ = self.recovery_mgr.should_recover(stopped_c)
        self.assertTrue(qualifies)

    def test_max_retries_safeguard(self):
        stopped_c = ContainerStats(
            container_id="333", name="crm-broken-1", service="frappe", image="frappe/bench:latest",
            status="exited", health_status="none", overall_health="STOPPED",
        )
        # Exceed max retries
        self.recovery_mgr.retry_counts["crm-broken-1"] = 3
        qualifies, reason = self.recovery_mgr.should_recover(stopped_c)
        self.assertFalse(qualifies)
        self.assertIn("exceeded", reason.lower())

    def test_dry_run_simulation(self):
        self.recovery_mgr.dry_run = True
        stopped_c = ContainerStats(
            container_id="444", name="crm-redis-1", service="redis", image="redis:alpine",
            status="exited", health_status="none", overall_health="STOPPED",
        )
        action = self.recovery_mgr.recover(stopped_c)
        self.assertEqual(action.action, "dry_run_restart")
        self.assertTrue(action.success)
        self.assertFalse(self.mock_client.restart_container.called)

    def test_live_recovery_success(self):
        self.mock_client.restart_container.return_value = True
        self.mock_client.inspect_containers.return_value = {
            "crm-redis-1": {"State": {"Status": "running"}}
        }

        stopped_c = ContainerStats(
            container_id="555", name="crm-redis-1", service="redis", image="redis:alpine",
            status="exited", health_status="none", overall_health="STOPPED",
        )
        action = self.recovery_mgr.recover(stopped_c)
        self.assertEqual(action.action, "restart")
        self.assertTrue(action.success)
        self.assertEqual(action.final_status, "running")
        self.mock_client.restart_container.assert_called_once_with("crm-redis-1", timeout=10)


class TestReportGenerator(unittest.TestCase):
    """Verifies JSON schema and Markdown report generation."""

    def setUp(self):
        self.test_dir = Path(tempfile.mkdtemp())
        self.sample_report = SystemHealthReport(
            report_id="report_test_12345",
            timestamp="2026-11-05T12:00:00Z",
            project="crm",
            overall_status="HEALTHY",
            summary={
                "total_containers": 1,
                "running_containers": 1,
                "stopped_containers": 0,
                "unhealthy_containers": 0,
                "warning_containers": 0,
                "total_cpu_percent": 15.0,
                "total_memory_usage_bytes": 500 * 1024 * 1024,
                "total_memory_usage_human": "500.0 MiB",
                "total_errors_in_logs": 0,
                "auto_recoveries_attempted": 0,
                "auto_recoveries_succeeded": 0,
            },
            thresholds={"cpu_warning_percent": 80.0, "memory_warning_percent": 80.0},
            containers=[
                ContainerStats(
                    container_id="ae71acbba1f4",
                    name="crm-frappe-1",
                    service="frappe",
                    image="frappe/bench:latest",
                    status="running",
                    health_status="healthy",
                    overall_health="HEALTHY",
                    cpu_percent=15.0,
                    memory_usage_bytes=500 * 1024 * 1024,
                    memory_limit_bytes=2 * 1024 * 1024 * 1024,
                    memory_percent=24.4,
                    memory_usage_human="500.0 MiB",
                    memory_limit_human="2.0 GiB",
                    network_io="10MB / 5MB",
                    block_io="20MB / 10MB",
                    pids=25,
                    uptime="2d 4h",
                    started_at="2026-11-03T11:39:14Z",
                )
            ],
            log_analyses={
                "crm-frappe-1": LogAnalysisResult(container_name="crm-frappe-1", scanned_lines=50)
            },
            recovery_actions=[],
            alerts=[],
        )

    def tearDown(self):
        shutil.rmtree(self.test_dir)

    def test_json_report_serialization(self):
        json_file = self.test_dir / "report.json"
        json_str = ReportGenerator.generate_json_report(self.sample_report, json_file)
        self.assertTrue(json_file.exists())
        data = json.loads(json_str)
        self.assertEqual(data["overall_status"], "HEALTHY")
        self.assertEqual(data["project"], "crm")
        self.assertEqual(len(data["containers"]), 1)
        self.assertEqual(data["containers"][0]["name"], "crm-frappe-1")

    def test_markdown_report_generation(self):
        md_file = self.test_dir / "report.md"
        md_str = ReportGenerator.generate_markdown_report(self.sample_report, md_file)
        self.assertTrue(md_file.exists())
        self.assertIn("# Frappe CRM — Docker Container Health & Monitoring Report", md_str)
        self.assertIn("crm-frappe-1", md_str)
        self.assertIn("🟢 **HEALTHY**", md_str)


class TestDockerClientErrorHandling(unittest.TestCase):
    """Verifies robust exception handling for Docker command execution."""

    @patch("subprocess.run")
    def test_docker_command_not_found(self, mock_run):
        mock_run.side_effect = FileNotFoundError("Executable not found")
        client = DockerClient()
        with self.assertRaises(DockerClientError) as ctx:
            client.run_cmd(["ps"])
        self.assertIn("not found in system PATH", str(ctx.exception))

    @patch("subprocess.run")
    def test_docker_command_timeout(self, mock_run):
        mock_run.side_effect = subprocess.TimeoutExpired(cmd=["docker", "ps"], timeout=5)
        client = DockerClient(timeout_sec=5)
        with self.assertRaises(DockerClientError) as ctx:
            client.run_cmd(["ps"])
        self.assertIn("timed out after 5s", str(ctx.exception))


if __name__ == "__main__":
    unittest.main()
