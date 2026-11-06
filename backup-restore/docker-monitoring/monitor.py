import json
import logging
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

# --------------------------------------------------
# PATHS AND CONFIGURATION
# --------------------------------------------------

BASE_DIR = Path(__file__).resolve().parent
CONFIG_PATH = BASE_DIR / "config.json"

try:
    CONFIG = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
except (FileNotFoundError, json.JSONDecodeError) as exc:
    print(f"Configuration error: {exc}")
    sys.exit(1)

REPORT_PATH = BASE_DIR / CONFIG["report_file"]
LOG_PATH = BASE_DIR / CONFIG["log_file"]

REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
LOG_PATH.parent.mkdir(parents=True, exist_ok=True)

logging.basicConfig(
    filename=str(LOG_PATH),
    level=logging.INFO,
    format="%(asctime)s %(levelname)s: %(message)s"
)

logger = logging.getLogger("docker-monitor")


# --------------------------------------------------
# DOCKER COMMAND EXECUTION
# --------------------------------------------------

def docker_command(*args):
    result = subprocess.run(
        ["docker", *args],
        capture_output=True,
        text=True,
        timeout=30
    )

    if result.returncode != 0:
        raise RuntimeError(
            result.stderr.strip() or "Docker command failed"
        )

    return result.stdout.strip()


# --------------------------------------------------
# DISCOVER F RAPPE CRM CONTAINERS
# --------------------------------------------------

def get_containers():
    output = docker_command(
        "ps", "-a", "--format", "{{json .}}"
    )

    containers = []

    for line in output.splitlines():
        if not line:
            continue

        item = json.loads(line)
        name = item.get("Names", "").lower()

        if any(
            term.lower() in name
            for term in CONFIG["container_name_contains"]
        ):
            containers.append(item)

    return containers


# --------------------------------------------------
# HEALTH STATUS
# --------------------------------------------------

def get_health(name):
    output = docker_command(
        "inspect",
        "--format",
        "{{if .State.Health}}{{.State.Health.Status}}{{else}}not-configured{{end}}",
        name
    )

    return output or "unknown"


# --------------------------------------------------
# CPU AND MEMORY USAGE
# --------------------------------------------------

def get_stats(name):
    output = docker_command(
        "stats",
        "--no-stream",
        "--format",
        "{{.CPUPerc}}|{{.MemUsage}}|{{.MemPerc}}",
        name
    )

    parts = output.split("|")

    if len(parts) != 3:
        raise RuntimeError("Unexpected Docker stats output")

    return {
        "cpu_percent": parts[0],
        "memory_usage": parts[1],
        "memory_percent": parts[2]
    }


# --------------------------------------------------
# LOG COLLECTION AND ERROR ANALYSIS
# --------------------------------------------------

def analyze_logs(name):
    output = docker_command(
        "logs",
        "--tail",
        str(CONFIG["log_tail_lines"]),
        name
    )

    patterns = CONFIG["error_patterns"]

    matches = [
        line for line in output.splitlines()
        if any(
            re.search(pattern, line, re.IGNORECASE)
            for pattern in patterns
        )
    ]

    return {
        "errors_found": len(matches),
        "error_samples": matches[:10]
    }


# --------------------------------------------------
# MAIN MONITORING FUNCTION
# --------------------------------------------------

def monitor(auto_restart=False):

    report = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "project": "Frappe CRM",
        "overall_status": "HEALTHY",
        "auto_restart_enabled": auto_restart,
        "container_count": 0,
        "containers": [],
        "error": None
    }

    try:
        containers = get_containers()

        for item in containers:

            name = item.get("Names", "unknown")
            status = item.get("Status", "unknown")
            running = status.lower().startswith("up")

            health = get_health(name) if running else "not-running"

            # Resource monitoring
            try:
                stats = get_stats(name) if running else {
                    "cpu_percent": None,
                    "memory_usage": None,
                    "memory_percent": None
                }
            except Exception as exc:
                logger.warning("Stats failed for %s: %s", name, exc)
                stats = {
                    "cpu_percent": None,
                    "memory_usage": None,
                    "memory_percent": None,
                    "collection_error": str(exc)
                }

            # Log monitoring
            try:
                logs = analyze_logs(name)
            except Exception as exc:
                logger.warning("Log collection failed for %s: %s", name, exc)
                logs = {
                    "errors_found": 0,
                    "error_samples": [],
                    "collection_error": str(exc)
                }

            # Status analysis
            recovery = "not-needed"

            if not running or health == "unhealthy":
                report["overall_status"] = "ATTENTION_REQUIRED"
                recovery = "not-attempted"

                # Only allow the disposable test container
                allowed = any(
                    token in name
                    for token in CONFIG["auto_restart_allowlist"]
                )

                if auto_restart and allowed:
                    try:
                        docker_command("start", name)
                        recovery = "restart-command-sent"
                        logger.info("Restart command sent to %s", name)

                    except Exception as exc:
                        recovery = f"failed: {exc}"
                        logger.exception("Recovery failed for %s", name)

            if logs["errors_found"] > 0:
                report["overall_status"] = "ATTENTION_REQUIRED"

            container_report = {
                "name": name,
                "status": status,
                "running": running,
                "health": health,
                "resources": stats,
                "log_analysis": logs,
                "recovery_action": recovery
            }

            report["containers"].append(container_report)

            logger.info(
                "Container checked: %s | Status: %s | Health: %s",
                name, status, health
            )

        report["container_count"] = len(containers)

        if not containers:
            report["overall_status"] = "NO_CONTAINERS_FOUND"

        logger.info(
            "Monitoring completed. Containers checked: %s",
            len(containers)
        )

    except Exception as exc:
        report["overall_status"] = "MONITORING_ERROR"
        report["error"] = str(exc)
        logger.exception("Monitoring failed")

    # Generate JSON health report
    REPORT_PATH.write_text(
        json.dumps(report, indent=4),
        encoding="utf-8"
    )

    print(json.dumps(report, indent=4))
    print(f"\nHealth report saved: {REPORT_PATH}")
    print(f"Monitoring log saved: {LOG_PATH}")

    return 1 if report["overall_status"] == "MONITORING_ERROR" else 0


# --------------------------------------------------
# PROGRAM ENTRY POINT
# --------------------------------------------------

if __name__ == "__main__":

    auto_restart = "--auto-restart" in sys.argv

    if auto_restart:
        print("Auto-recovery mode enabled.")

    else:
        print("Monitoring mode enabled. No containers will be restarted.")

    sys.exit(monitor(auto_restart=auto_restart))