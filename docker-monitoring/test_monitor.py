
import json
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent))
import monitor


def container(status="exited"):
    return {
        "Id": "test123",
        "Name": "/crm-frappe-1",
        "Config": {
            "Image": "frappe/bench:latest",
            "Labels": {
                "com.docker.compose.project": "crm",
                "com.docker.compose.service": "frappe"
            }
        },
        "State": {
            "Status": status,
            "ExitCode": 0,
            "OOMKilled": False,
            "RestartCount": 0
        },
        "HostConfig": {"RestartPolicy": {"Name": "no"}}
    }


class TestDockerMonitor(unittest.TestCase):

    def setUp(self):
        self.config = {
            "log_lines": 100,
            "keywords": ["error", "critical"],
            "restart_allowlist": []
        }

    @patch("monitor.docker")
    def test_discovery_filters_unrelated_containers(self, docker):
        unrelated = container()
        unrelated["Name"] = "/other-project-app"
        unrelated["Config"]["Labels"]["com.docker.compose.project"] = "other"

        docker.side_effect = [
            "id1\nid2",
            json.dumps([container(), unrelated])
        ]

        result = monitor.discover()
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["Name"], "/crm-frappe-1")

    @patch("monitor.analyse_logs", return_value=[])
    @patch("monitor.docker")
    def test_recovery_is_blocked_without_allowlist(self, docker, logs):
        result = monitor.monitor(
            container(), {}, self.config, True
        )

        self.assertEqual(result["recovery"], "blocked_not_allowlisted")
        docker.assert_not_called()

    @patch("monitor.analyse_logs", return_value=[])
    @patch("monitor.docker")
    def test_approved_recovery_reinspects_container(self, docker, logs):
        self.config["restart_allowlist"] = ["crm-frappe-1"]
        docker.side_effect = [
            "",
            json.dumps([container("running")])
        ]

        result = monitor.monitor(
            container(), {}, self.config, True
        )

        self.assertEqual(result["status"], "running")
        self.assertEqual(result["status_before_recovery"], "exited")
        self.assertEqual(result["recovery"], "started_and_reinspected")
        self.assertEqual(docker.call_count, 2)

    def test_missing_container_is_critical(self):
        result = monitor.classify([], ["crm-redis-1"], [])
        self.assertEqual(result, "critical")

    def test_unhealthy_container_is_critical(self):
        item = {
            "status": "running",
            "health": "unhealthy",
            "log_errors": [],
            "log_collection_error": None
        }
        self.assertEqual(monitor.classify([item], [], []), "critical")


if __name__ == "__main__":
    unittest.main(verbosity=2)
