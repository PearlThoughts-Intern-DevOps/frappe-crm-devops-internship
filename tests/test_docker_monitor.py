import json
import tempfile
from pathlib import Path
import unittest
from unittest.mock import patch

import docker_monitor


class DockerMonitorTests(unittest.TestCase):
    def test_summarize_container_extracts_status_and_health(self):
        container = {
            "Id": "1234567890abcdef",
            "Name": "/crm-frappe-1",
            "Config": {"Image": "frappe/bench:latest"},
            "State": {
                "Status": "running",
                "Health": {"Status": "healthy"},
                "ExitCode": 0,
            },
        }

        result = docker_monitor.summarize_container(container)

        self.assertEqual(result["id"], "1234567890ab")
        self.assertEqual(result["name"], "crm-frappe-1")
        self.assertEqual(result["status"], "running")
        self.assertEqual(result["health"], "healthy")
    @patch("docker_monitor.run_docker", return_value="12.50%|100MiB / 2GiB|4.88%")

    def test_get_container_stats_parses_cpu_and_memory(self, mock_run_docker):

      result = docker_monitor.get_container_stats("container123")

      self.assertEqual(result["cpu_percent"], 12.5)
      self.assertEqual(result["memory_usage"], "100MiB")
      self.assertEqual(result["memory_limit"], "2GiB")
      self.assertEqual(result["memory_percent"], 4.88)
      mock_run_docker.assert_called_once()
    @patch(
        "docker_monitor.run_docker",
        return_value=(
            "ERROR: failed to connect\n"
            "[Warning] error reading packets\n"
            "GET /ErrorPage.js 200\n"
            "1:M * <bf> { bf-error-rate : 0.01 }\n"
        ),
    )
    def test_collect_log_errors_ignores_warnings_and_substrings(self, mock_run_docker):
        result = docker_monitor.collect_log_errors("container123")

        self.assertEqual(result["error_count"], 1)
        self.assertEqual(result["error_samples"], ["ERROR: failed to connect"])
        mock_run_docker.assert_called_once_with(
            "logs",
            "--tail",
            "100",
            "container123",
            include_stderr=True,
        )
    def test_build_report_combines_container_checks(self):
        container = {
            "Id": "1234567890abcdef",
            "Name": "/crm-frappe-1",
            "Config": {"Image": "frappe/bench:latest"},
            "State": {
                "Status": "running",
                "Health": {"Status": "healthy"},
                "ExitCode": 0,
            },
        }
        stats = {
            "cpu_percent": 12.5,
            "memory_usage": "100MiB",
            "memory_limit": "2GiB",
            "memory_percent": 4.88,
        }
        logs = {"error_count": 0, "error_samples": []}

        with (
            patch.object(
                docker_monitor,
                "discover_containers",
                return_value=[container],
            ),
            patch.object(
                docker_monitor,
                "get_container_stats",
                return_value=stats,
            ),
            patch.object(
                docker_monitor,
                "collect_log_errors",
                return_value=logs,
            ),
        ):
            report = docker_monitor.build_report()

        self.assertEqual(report["overall_status"], "healthy")
        self.assertEqual(report["summary"]["total_containers"], 1)
        self.assertEqual(report["summary"]["running_containers"], 1)
        self.assertEqual(report["containers"][0]["resources"], stats)
        self.assertEqual(report["containers"][0]["logs"], logs)

    def test_auto_restart_starts_stopped_container(self):
        stopped_container =  {
            "Id": "1234567890abcdef",
            "Name": "/crm-redis-1",
            "Config": {"Image": "redis:alpine"},
            "State": {"Status": "exited", "ExitCode": 1},
         }
        running_container = {
            **stopped_container,
            "State": {"Status": "running", "ExitCode": 0},
        }

        with (
            patch.object(
                docker_monitor,
                "discover_containers",
                return_value=[stopped_container],
            ),
            patch.object(
                docker_monitor,
                "start_container",
                return_value=running_container,
            ) as start_mock,
            patch.object(docker_monitor, "get_container_stats", return_value={}),
            patch.object(
                docker_monitor,
                "collect_log_errors",
                return_value={"error_count": 0, "error_samples": []},
            ),
        ):
            report = docker_monitor.build_report(auto_restart=True)

        start_mock.assert_called_once_with("1234567890abcdef")
        self.assertEqual(report["containers"][0]["status"], "running")
        self.assertEqual(report["summary"]["running_containers"], 1)
    def test_auto_restart_is_off_by_default(self):
        stopped_container = {
            "Id": "1234567890abcdef",
            "Name": "/crm-redis-1",
            "Config": {"Image": "redis:alpine"},
            "State": {"Status": "exited", "ExitCode": 1},
        }

        with (
            patch.object(
                docker_monitor,
                "discover_containers",
                return_value=[stopped_container],
            ),
            patch.object(docker_monitor, "start_container") as start_mock,
            patch.object(
                docker_monitor,
                "collect_log_errors",
                return_value={"error_count": 0, "error_samples": []},
            ),
        ):
            docker_monitor.build_report()

        start_mock.assert_not_called()
    @patch(
        "docker_monitor.run_docker",
        side_effect=[
            "1234567890abcdef\n",
            '[{"Id": "1234567890abcdef", "State": {"Status": "running"}}]',
        ],
    )
    def test_start_container_starts_then_refreshes_details(self, mock_run_docker):
        result = docker_monitor.start_container("1234567890abcdef")

        self.assertEqual(result["State"]["Status"], "running")
        mock_run_docker.assert_any_call("start", "1234567890abcdef")
        mock_run_docker.assert_any_call("inspect", "1234567890abcdef")
    @patch(
        "docker_monitor.run_docker",
        side_effect=[
            "container123\n",
            '[{"Id": "container123", "State": {"Status": "running"}}]',
        ],
    )

    def test_discover_containers_filters_project_and_inspects_ids(self, mock_run_docker):

         containers = docker_monitor.discover_containers()

         self.assertEqual(len(containers), 1)
         self.assertEqual(containers[0]["Id"], "container123")
         mock_run_docker.assert_any_call(
            "ps",
            "--all",
            "--quiet",
            "--filter",
            "label=com.docker.compose.project=crm",
        )
         mock_run_docker.assert_any_call("inspect", "container123")
    def test_main_writes_json_report_to_file(self):
        report = {"overall_status": "healthy", "containers": []}

        with tempfile.TemporaryDirectory() as temp_dir:
            output_path = Path(temp_dir) / "health.json"

            with patch.object(
                docker_monitor,
                "build_report",
                return_value=report,
            ):
                result = docker_monitor.main(["--output", str(output_path)])

            saved_report = json.loads(output_path.read_text(encoding="utf-8"))

            self.assertEqual(result, 0)
            self.assertEqual(saved_report, report)
if __name__ == "__main__":
    unittest.main()