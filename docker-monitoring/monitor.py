
#!/usr/bin/env python3
"""Efficient, allowlisted Docker monitoring for Frappe CRM."""

import argparse
import json
import logging
import subprocess
import time
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent
CONFIG = ROOT / "config.json"
REPORTS = ROOT / "reports"
LOGS = ROOT / "logs"

PROJECT = "crm"
SERVICES = {"frappe", "mariadb", "redis"}
EXPECTED = {f"crm-{service}-1" for service in SERVICES}


def docker(*args):
    result = subprocess.run(
        ["docker", *map(str, args)],
        capture_output=True, text=True, timeout=30
    )
    if result.returncode:
        raise RuntimeError(result.stderr.strip() or "Docker command failed")
    return result.stdout


def load_config():
    defaults = {
        "log_lines": 100,
        "keywords": ["error", "critical", "fatal", "exception", "traceback"],
        "restart_allowlist": []
    }
    if CONFIG.exists():
        supplied = json.loads(CONFIG.read_text(encoding="utf-8"))
        if not isinstance(supplied, dict):
            raise ValueError("Configuration must be a JSON object")
        defaults.update(supplied)

    defaults["log_lines"] = max(1, min(int(defaults["log_lines"]), 1000))
    if not isinstance(defaults["keywords"], list):
        raise ValueError("keywords must be a list")
    if not isinstance(defaults["restart_allowlist"], list):
        raise ValueError("restart_allowlist must be a list")
    if not set(defaults["restart_allowlist"]).issubset(EXPECTED):
        raise ValueError("Recovery allowlist contains an unapproved container")
    return defaults


def discover():
    ids = docker(
        "ps", "-aq",
        "--filter", f"label=com.docker.compose.project={PROJECT}"
    ).split()
    if not ids:
        return []

    return [
        item for item in json.loads(docker("inspect", *ids))
        if (item.get("Config", {}).get("Labels") or {}).get(
            "com.docker.compose.project"
        ) == PROJECT
        and (item.get("Config", {}).get("Labels") or {}).get(
            "com.docker.compose.service"
        ) in SERVICES
        and item.get("Name", "").lstrip("/") in EXPECTED
    ]


def collect_stats(containers):
    running = [
        item["Id"] for item in containers
        if item.get("State", {}).get("Status") == "running"
    ]
    if not running:
        return {}

    output = docker(
        "stats", "--no-stream", "--format", "{{json .}}", *running
    )
    return {
        item["Name"]: {
            "cpu": item.get("CPUPerc", "unavailable"),
            "memory": item.get("MemUsage", "unavailable")
        }
        for item in (json.loads(line) for line in output.splitlines() if line)
    }


def analyse_logs(container_id, config):
    keywords = [word.lower() for word in config["keywords"]]
    matches = []
    output = docker("logs", "--tail", config["log_lines"], container_id)

    for line in output.splitlines():
        found = [word for word in keywords if word in line.lower()]
        if found:
            matches.append({"message": line[:500], "keywords": found})
    return matches


def monitor(container, stats, config, auto_restart):
    name = container["Name"].lstrip("/")
    state = container.get("State", {})
    initial_status = state.get("Status", "unknown")
    recovery = "not_requested"

    if auto_restart and initial_status in ("exited", "created"):
        if name in config["restart_allowlist"]:
            try:
                docker("start", container["Id"])
                container = json.loads(docker("inspect", container["Id"]))[0]
                recovery = "started_and_reinspected"
            except (RuntimeError, subprocess.TimeoutExpired) as exc:
                recovery = f"failed: {exc}"
        else:
            recovery = "blocked_not_allowlisted"

    state = container.get("State", {})
    status = state.get("Status", "unknown")
    health = state.get("Health", {}).get("Status", "not_configured")
    labels = container.get("Config", {}).get("Labels") or {}

    try:
        log_errors = analyse_logs(container["Id"], config)
        log_error = None
    except (RuntimeError, subprocess.TimeoutExpired) as exc:
        log_errors, log_error = [], str(exc)

    alerts = []
    if status != "running":
        alerts.append("container_not_running")
    if health == "unhealthy":
        alerts.append("health_check_unhealthy")
    if log_errors:
        alerts.append("log_errors_detected")
    if log_error:
        alerts.append("log_collection_failed")

    resource = stats.get(name, {})
    return {
        "name": name,
        "service": labels.get("com.docker.compose.service"),
        "image": container.get("Config", {}).get("Image"),
        "status": status,
        "status_before_recovery": initial_status,
        "health": health,
        "oom_killed": state.get("OOMKilled", False),
        "exit_code": state.get("ExitCode"),
        "restart_count": state.get("RestartCount", 0),
        "restart_policy": container.get("HostConfig", {}).get(
            "RestartPolicy", {}
        ).get("Name", "unknown"),
        "cpu": resource.get("cpu", "unavailable"),
        "memory": resource.get("memory", "unavailable"),
        "log_errors": log_errors,
        "log_collection_error": log_error,
        "alerts": alerts,
        "recovery": recovery
    }


def classify(results, missing, errors):
    if missing or errors or any(
        item["status"] != "running" or item["health"] == "unhealthy"
        for item in results
    ):
        return "critical"

    if any(
        item["health"] != "healthy"
        or item["log_errors"]
        or item["log_collection_error"]
        for item in results
    ):
        return "degraded"

    return "healthy"


def run_once(config, auto_restart):
    containers = discover()
    stats = collect_stats(containers)
    results, errors = [], []

    for container in containers:
        name = container["Name"].lstrip("/")
        try:
            results.append(monitor(container, stats, config, auto_restart))
        except (RuntimeError, subprocess.TimeoutExpired) as exc:
            logging.exception("Inspection failed: %s", name)
            errors.append({"container": name, "error": str(exc)})

    found = {item["name"] for item in results}
    missing = sorted(EXPECTED - found)

    report = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "project": PROJECT,
        "mode": "recovery_opt_in" if auto_restart else "read_only",
        "overall_health": classify(results, missing, errors),
        "summary": {
            "expected": len(EXPECTED),
            "monitored": len(results),
            "running": sum(x["status"] == "running" for x in results),
            "stopped": sum(x["status"] != "running" for x in results),
            "missing_containers": missing,
            "with_alerts": sum(bool(x["alerts"]) for x in results),
            "inspection_errors": len(errors)
        },
        "containers": results,
        "errors": errors
    }

    stamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S_%f")
    path = REPORTS / f"health_{stamp}.json"
    path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    logging.info("Report generated: %s", path)
    print(f"Report: {path}")
    print(json.dumps(report["summary"], indent=2))
    print(f"Overall health: {report['overall_health']}")


def main():
    parser = argparse.ArgumentParser(description="Frappe CRM Docker Monitor")
    parser.add_argument("--interval", type=int, default=0)
    parser.add_argument("--auto-restart", action="store_true")
    args = parser.parse_args()
    if args.interval < 0:
        parser.error("--interval cannot be negative")

    REPORTS.mkdir(parents=True, exist_ok=True)
    LOGS.mkdir(parents=True, exist_ok=True)
    logging.basicConfig(
        filename=LOGS / "monitor.log",
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s"
    )

    try:
        config = load_config()
        while True:
            run_once(config, args.auto_restart)
            if not args.interval:
                break
            time.sleep(args.interval)
    except (RuntimeError, ValueError, OSError, json.JSONDecodeError,
            subprocess.TimeoutExpired) as exc:
        logging.exception("Monitoring failed")
        parser.exit(1, f"Monitoring failed: {exc}\n")


if __name__ == "__main__":
    main()
