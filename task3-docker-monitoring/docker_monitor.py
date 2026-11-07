import argparse
import docker
import json
import logging
from datetime import datetime, timezone
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
REPORT_DIR = BASE_DIR / "reports"
LOG_DIR = BASE_DIR / "logs"

REPORT_DIR.mkdir(exist_ok=True)
LOG_DIR.mkdir(exist_ok=True)

logging.basicConfig(
    filename=LOG_DIR / "monitoring.log",
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)

FRAPPE_CONTAINERS = {
    "crm-frappe-1",
    "crm-mariadb-1",
    "crm-redis-1",
    "frappe-inspect"
}
# Only these Frappe CRM containers are eligible for auto-recovery.
RECOVERY_CONTAINERS = {
    "crm-frappe-1",
    "crm-mariadb-1",
    "crm-redis-1"
    
}

ERROR_KEYWORDS = (
    "error", "exception", "fatal", "traceback", "critical"
)


def connect_docker():
    try:
        client = docker.from_env()
        client.ping()
        logging.info("Connected to Docker successfully")
        return client
    except docker.errors.DockerException:
        logging.exception("Docker connection failed")
        raise


def get_cpu_percentage(container):
    """Calculate CPU usage using two consecutive Docker stats samples."""
    stream = None

    try:
        stream = container.stats(stream=True, decode=True)

        first = next(stream)
        second = next(stream)

        cpu1 = first["cpu_stats"]
        cpu2 = second["cpu_stats"]

        cpu_delta = (
            cpu2["cpu_usage"]["total_usage"]
            - cpu1["cpu_usage"]["total_usage"]
        )

        system_delta = (
            cpu2.get("system_cpu_usage", 0)
            - cpu1.get("system_cpu_usage", 0)
        )

        online_cpus = cpu2.get("online_cpus")

        if not online_cpus:
            online_cpus = len(
                cpu2["cpu_usage"].get("percpu_usage", [])
            )

        if cpu_delta > 0 and system_delta > 0 and online_cpus > 0:
            return round(
                (cpu_delta / system_delta) * online_cpus * 100, 2
            )

        return 0.0

    except (docker.errors.APIError, KeyError, StopIteration, TypeError):
        logging.exception(
            "Unable to calculate CPU for %s", container.name
        )
        return None

    finally:
        if stream is not None:
            stream.close()


def get_resource_usage(container, status):
    """Collect CPU and memory information for running containers."""
    if status != "running":
        return {
            "cpu_percent": None,
            "memory_usage_mb": None,
            "memory_limit_mb": None,
            "memory_percent": None
        }

    try:
        stats = container.stats(stream=False)

        memory_stats = stats.get("memory_stats", {})
        memory_usage = memory_stats.get("usage", 0)
        memory_limit = memory_stats.get("limit", 0)

        memory_percent = None
        if memory_limit > 0:
            memory_percent = round(
                (memory_usage / memory_limit) * 100, 2
            )

        return {
            "cpu_percent": get_cpu_percentage(container),
            "memory_usage_mb": round(memory_usage / (1024 ** 2), 2),
            "memory_limit_mb": round(memory_limit / (1024 ** 2), 2),
            "memory_percent": memory_percent
        }

    except (docker.errors.APIError, KeyError, TypeError):
        logging.exception(
            "Unable to collect resource usage for %s", container.name
        )
        return {
            "cpu_percent": None,
            "memory_usage_mb": None,
            "memory_limit_mb": None,
            "memory_percent": None
        }


def analyze_logs(container):
    """Scan the last 100 log lines for common error indicators."""
    try:
        raw_logs = container.logs(
            tail=100,
            timestamps=True
        )

        log_text = raw_logs.decode("utf-8", errors="replace")
        lines = log_text.splitlines()

        error_lines = [
            line for line in lines
            if any(keyword in line.lower() for keyword in ERROR_KEYWORDS)
        ]

        return {
            "log_lines_scanned": len(lines),
            "log_error_count": len(error_lines),
            "log_error_samples": error_lines[:20]
        }

    except docker.errors.APIError:
        logging.exception(
            "Unable to collect logs for %s", container.name
        )
        return {
            "log_lines_scanned": 0,
            "log_error_count": 0,
            "log_error_samples": [],
            "log_collection_error": True
        }


def get_container_details(container):
    """Collect container status, health, resource usage and logs."""
    try:
        container.reload()

        state = container.attrs.get("State", {})
        status = state.get("Status", "unknown")
        health = state.get("Health", {}).get(
            "Status", "not_configured"
        )

        details = {
            "container_id": container.short_id,
            "container_name": container.name,
            "project": (
                "Frappe CRM"
                if container.name in FRAPPE_CONTAINERS
                else "Other Docker Project"
            ),
            "image": container.image.tags,
            "status": status,
            "health": health,
            "exit_code": state.get("ExitCode"),
            "restart_count": container.attrs.get("RestartCount", 0)
        }

        details.update(get_resource_usage(container, status))
        details.update(analyze_logs(container))

        return details

    except docker.errors.APIError:
        logging.exception(
            "Could not inspect container %s", container.name
        )
        return {
            "container_name": container.name,
            "status": "inspection_error"
        }

def recover_container(container):
    """Restart an eligible stopped Frappe CRM container."""
    if container.name not in RECOVERY_CONTAINERS:
        return "not_eligible"

    try:
        container.reload()
        status = container.status

        if status not in ("exited", "created"):
            return "not_needed"

        logging.warning(
            "Attempting recovery for container %s",
            container.name
        )

        container.start()
        container.reload()

        if container.status == "running":
            logging.info(
                "Successfully restarted %s",
                container.name
            )
            return "restarted"

        return "restart_not_confirmed"

    except docker.errors.APIError:
        logging.exception(
            "Recovery failed for %s",
            container.name
        )
        return "failed"
def monitor_containers(auto_restart=False):
    client = connect_docker()

    report = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "total_containers": 0,
        "running": 0,
        "stopped": 0,
        "unhealthy": 0,
        "frappe_container_count": 0,
        "frappe_containers": [],
        "containers": []
    }

    try:
        containers = client.containers.list(all=True)

        for container in containers:

            if auto_restart:
                recovery_status = recover_container(container)
            else:
                recovery_status = "disabled"
  
            details = get_container_details(container)
            details["recovery_status"] = recovery_status

            report["containers"].append(details)

            status = details.get("status")

            if status == "running":
                report["running"] += 1
            elif status == "exited":
                report["stopped"] += 1

            if details.get("health") == "unhealthy":
                report["unhealthy"] += 1

            if details.get("project") == "Frappe CRM":
                report["frappe_containers"].append(details)

        report["total_containers"] = len(containers)
        report["frappe_container_count"] = len(
            report["frappe_containers"]
        )

        report_path = REPORT_DIR / "health_report.json"

        with report_path.open("w", encoding="utf-8") as file:
            json.dump(report, file, indent=4)

        logging.info("Health report generated successfully")

        print("\nDocker Monitoring Summary")
        print("-------------------------")
        print(f"Total containers : {report['total_containers']}")
        print(f"Running          : {report['running']}")
        print(f"Stopped          : {report['stopped']}")
        print(f"Unhealthy        : {report['unhealthy']}")
        print(f"Frappe containers: {report['frappe_container_count']}")
        print(f"Report saved to  : {report_path}")
        print(f"\nReport saved to: {report_path}")

    finally:
        client.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Docker Container Monitoring Tool"
    )

    parser.add_argument(
        "--auto-restart",
        action="store_true",
        help="Restart eligible stopped Frappe CRM containers"
    )

    args = parser.parse_args()
    monitor_containers(auto_restart=args.auto_restart)