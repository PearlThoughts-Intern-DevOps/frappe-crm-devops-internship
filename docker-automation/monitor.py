
import argparse
import json
import logging
import os
import sys
import time
from datetime import datetime, timezone

import docker
from docker.errors import DockerException

PROJECT = os.getenv("FRAPPE_COMPOSE_PROJECT", "crm")

NAME_PREFIX = os.getenv("FRAPPE_CONTAINER_PREFIX", "frappe")

CPU_WARNING = 80
MEMORY_WARNING = 80
LOG_LINES = 200
WATCH_SECONDS = 30

ERROR_WORDS = ["error", "exception", "traceback", "critical", "fatal"]

RUN_ONCE_SERVICES = ["configurator", "create-site", "migration"]

REPORT_FILE = "reports/health_report.json"
LOG_FILE = "logs/monitor.log"
TEST_CONTAINER_NAME = "frappe-monitor-recovery-test"

os.makedirs("logs", exist_ok=True)
os.makedirs("reports", exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler(), logging.FileHandler(LOG_FILE)],
)
log = logging.getLogger("monitor")

def find_frappe_containers(client):
    found = []

    for container in client.containers.list(all=True):

        if container.name == TEST_CONTAINER_NAME:
            continue

        if PROJECT:

            if container.labels.get("com.docker.compose.project") == PROJECT:
                found.append(container)
        else:

            if container.name.startswith(NAME_PREFIX):
                found.append(container)

    return found

def get_cpu_percent(stats):
    try:
        cpu_now = stats["cpu_stats"]["cpu_usage"]["total_usage"]
        cpu_before = stats["precpu_stats"]["cpu_usage"]["total_usage"]
        system_now = stats["cpu_stats"]["system_cpu_usage"]
        system_before = stats["precpu_stats"]["system_cpu_usage"]

        cores = stats["cpu_stats"].get("online_cpus")
        if not cores:
            cores = len(stats["cpu_stats"]["cpu_usage"].get("percpu_usage") or []) or 1

        cpu_used = cpu_now - cpu_before
        system_total = system_now - system_before

        if system_total > 0 and cpu_used >= 0:
            return round(cpu_used / system_total * cores * 100, 2)
    except (KeyError, TypeError):
        pass

    return None

def get_memory(stats):
    try:
        memory = stats["memory_stats"]

        cache = memory.get("stats", {}).get("inactive_file", 0)

        used_mb = (memory["usage"] - cache) / 1024 / 1024
        limit_mb = memory["limit"] / 1024 / 1024
        percent = used_mb / limit_mb * 100

        return round(used_mb, 1), round(limit_mb, 1), round(percent, 1)
    except (KeyError, TypeError, ZeroDivisionError):
        return None, None, None

def analyze_logs(container):
    result = {"log_available": True, "total_errors": 0, "sample_errors": []}

    try:
        raw_logs = container.logs(tail=LOG_LINES, timestamps=True)
        text = raw_logs.decode("utf-8", errors="replace")

        for line in text.splitlines():
            lowercase_line = line.lower()
            if any(word in lowercase_line for word in ERROR_WORDS):
                result["total_errors"] += 1

                if len(result["sample_errors"]) < 10:
                    result["sample_errors"].append(line[:300])

    except Exception:
        log.exception("Could not read logs of %s", container.name)
        result["log_available"] = False

    return result

def check_container(container):
    container.reload()

    state = container.attrs["State"]
    status = container.status
    exit_code = state.get("ExitCode")
    service = container.labels.get("com.docker.compose.service", container.name)

    health = state.get("Health", {}).get("Status", "not_configured")

    info = {
        "name": container.name,
        "status": status,
        "health": health,
        "exit_code": exit_code,
        "cpu_percent": None,
        "memory_usage_mb": None,
        "memory_limit_mb": None,
        "memory_percent": None,
        "is_stopped": False,
        "is_unhealthy": False,
        "issues": [],
    }

    if status == "running":

        try:
            stats = container.stats(stream=False)
            info["cpu_percent"] = get_cpu_percent(stats)
            used, limit, percent = get_memory(stats)
            info["memory_usage_mb"] = used
            info["memory_limit_mb"] = limit
            info["memory_percent"] = percent
        except Exception:
            log.exception("Could not read stats of %s", container.name)
            info["issues"].append("could not read CPU/memory")

        if health == "unhealthy":
            info["is_unhealthy"] = True
            info["issues"].append("unhealthy (Docker health check is failing)")

        if info["cpu_percent"] is not None and info["cpu_percent"] > CPU_WARNING:
            info["issues"].append(f"high CPU: {info['cpu_percent']}%")

        if info["memory_percent"] is not None and info["memory_percent"] > MEMORY_WARNING:
            info["issues"].append(f"high memory: {info['memory_percent']}%")

    elif status in ("exited", "dead", "created"):

        finished_normally = service in RUN_ONCE_SERVICES and exit_code == 0
        if not finished_normally:
            info["is_stopped"] = True
            info["issues"].append(f"stopped (exit code {exit_code})")

    else:

        info["issues"].append(f"unexpected state: {status}")

    info["log_analysis"] = analyze_logs(container)
    error_count = info["log_analysis"]["total_errors"]
    if error_count > 0:
        info["issues"].append(f"{error_count} error lines found in logs")

    return info

def docker_is_local():
    docker_host = os.getenv("DOCKER_HOST", "")
    return docker_host == "" or docker_host.startswith(("unix://", "npipe://"))

def restart_container(container, info):

    if container.name != TEST_CONTAINER_NAME:
        log.warning("Recovery blocked for %s (not the disposable test container)", container.name)
        return None

    if not docker_is_local():
        log.warning("Recovery blocked: Docker is not local")
        return None

    if not info["is_stopped"]:
        return None

    action = {"container": container.name, "result": "failed"}

    try:
        log.warning("Restarting disposable test container")
        container.restart(timeout=10)
        time.sleep(3)
        container.reload()

        if container.status == "running":
            action["result"] = "restarted"
            log.info("Recovery successful")
        else:
            log.error("Recovery failed (state: %s)", container.status)

    except DockerException:
        log.exception("Recovery failed")

    return action

def run_check(client):
    containers = find_frappe_containers(client)
    if not containers:
        log.warning("No Frappe containers found. Is FRAPPE_COMPOSE_PROJECT set correctly?")

    all_results = []

    for container in containers:
        log.info("Checking container: %s", container.name)

        try:
            info = check_container(container)
        except Exception:
            log.exception("Check failed for %s", container.name)
            info = {"name": container.name, "status": "unknown", "health": "unknown",
                    "is_stopped": False, "is_unhealthy": False,
                    "issues": ["check failed, see logs/monitor.log"]}
        all_results.append(info)

    stopped = [r["name"] for r in all_results if r["is_stopped"]]
    unhealthy = [r["name"] for r in all_results if r["is_unhealthy"]]
    running_count = sum(1 for r in all_results if r["status"] == "running")

    if not all_results:
        overall = "UNKNOWN"
    elif stopped or unhealthy:
        overall = "CRITICAL"
    elif any(r["issues"] for r in all_results):
        overall = "WARNING"
    else:
        overall = "HEALTHY"

    report = {
        "project": PROJECT or NAME_PREFIX,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "overall_status": overall,
        "total_containers": len(all_results),
        "running_containers": running_count,
        "stopped_containers": stopped,
        "unhealthy_containers": unhealthy,
        "containers": all_results,

        "auto_recovery": {"scope": "disposable test container only"},
    }

    try:
        with open(REPORT_FILE, "w") as file:
            json.dump(report, file, indent=2)
        log.info("JSON report saved: %s", REPORT_FILE)
    except OSError:
        log.exception("Could not save the report file")

    log.info("Monitoring finished: %s", overall)
    return report

def test_recovery(client):
    test_container = None
    try:
        log.info("Creating disposable recovery test container")
        test_container = client.containers.run(
            "alpine", ["sleep", "300"], name=TEST_CONTAINER_NAME, detach=True
        )

        log.info("Stopping disposable test container")
        test_container.stop(timeout=1)

        log.info("Testing automatic recovery")
        info = check_container(test_container)
        action = restart_container(test_container, info)

        if action and action["result"] == "restarted":
            log.info("AUTO-RECOVERY TEST PASSED")
            return True

        log.error("AUTO-RECOVERY TEST FAILED")
        return False

    except DockerException:
        log.exception("Recovery test could not run")
        return False

    finally:

        if test_container is not None:
            log.info("Removing disposable test container")
            try:
                test_container.remove(force=True)
            except DockerException:
                log.exception("Could not remove the test container")

def main():
    parser = argparse.ArgumentParser(description="Frappe CRM Docker monitor")
    parser.add_argument("--watch", action="store_true",
                        help="keep checking every 30 seconds")
    parser.add_argument("--test-recovery", action="store_true",
                        help="test auto-recovery with a disposable container")
    args = parser.parse_args()

    try:
        client = docker.from_env()
        client.ping()
        log.info("Docker connected successfully")
    except DockerException as error:
        log.error("Cannot connect to Docker. Is it running? (%s)", error)
        sys.exit(1)

    if args.test_recovery:
        sys.exit(0 if test_recovery(client) else 1)

    log.info("Starting Frappe CRM monitoring")
    try:
        while True:
            try:
                run_check(client)
            except DockerException:
                log.exception("Docker error during the check")

            if not args.watch:
                break
            time.sleep(WATCH_SECONDS)

    except KeyboardInterrupt:
        log.info("Stopped by user")

if __name__ == "__main__":
    main()