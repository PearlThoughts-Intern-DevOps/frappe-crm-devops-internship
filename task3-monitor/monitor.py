#!/usr/bin/env python3
"""Docker monitoring and auto-recovery tool for Frappe CRM.

  python3 monitor.py                   # check only, writes a JSON health report
  python3 monitor.py --auto-restart    # also start stopped containers of this project
  python3 monitor.py --project crm-restore-test
"""
import argparse
import json
import logging
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

LOG_PATTERNS = ["error", "exception", "traceback", "critical", "fatal", "refused"]
IGNORE_LINES = ["error-rate"]          # startup config lines (e.g. Redis bf-error-rate), not errors
STOPPED_STATES = ("exited", "dead", "created")
RESTARTS = {}                          # restarts done per container during this run (used by --watch)

logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s",
                    handlers=[logging.StreamHandler(), logging.FileHandler("monitor.log")])
log = logging.getLogger("monitor")


class MonitorError(Exception):
    """Expected failure (docker missing, no containers, ...)."""


def docker(*args, check=True):
    try:
        p = subprocess.run(["docker", *args], capture_output=True, text=True, timeout=60)
    except FileNotFoundError:
        raise MonitorError("docker command not found - is Docker installed and on PATH?")
    except subprocess.TimeoutExpired:
        raise MonitorError(f"'docker {args[0]}' timed out")
    if check and p.returncode != 0:
        raise MonitorError(f"docker {args[0]} failed: {p.stderr.strip()[:300]}")
    return p


def list_containers(project):
    """Only containers that belong to this compose project - never anything else."""
    out = docker("ps", "-a", "--filter", f"label=com.docker.compose.project={project}",
                 "--format", "{{.Names}}").stdout
    return sorted(out.split())


def inspect(name):
    data = json.loads(docker("inspect", name).stdout)[0]
    state = data["State"]
    return {"name": name, "image": data["Config"]["Image"], "status": state["Status"],
            "health": state.get("Health", {}).get("Status", "none"),
            "exit_code": state["ExitCode"], "restart_count": data.get("RestartCount", 0),
            "started_at": state["StartedAt"],
            # compose records what each service depends on; containers with none must be started first
            "dependencies": len([d for d in data["Config"].get("Labels", {})
                                 .get("com.docker.compose.depends_on", "").split(",") if d])}


def percent(text):
    try:
        return float(text.strip().rstrip("%"))
    except ValueError:
        return 0.0


def get_stats(names):
    if not names:
        return {}
    out = docker("stats", "--no-stream", "--format", "{{json .}}", *names).stdout
    stats = {}
    for line in out.splitlines():
        s = json.loads(line)
        stats[s["Name"]] = {"cpu_percent": percent(s["CPUPerc"]), "memory_percent": percent(s["MemPerc"]),
                            "memory_usage": s["MemUsage"]}
    return stats


def analyze_logs(name, tail):
    p = docker("logs", "--tail", str(tail), name, check=False)
    lines = (p.stdout + p.stderr).split("\n")          # split on \n only: progress bars use \r
    counts, errors = {}, []
    for line in lines:
        low = line.lower()
        if any(x in low for x in IGNORE_LINES):
            continue
        if "[warning]" in low and "[error]" not in low:
            continue                                    # the service itself labels this a warning
        hits = [k for k in LOG_PATTERNS if k in low]
        for k in hits:
            counts[k] = counts.get(k, 0) + 1
        if hits:
            errors.append(line.strip()[:200])
    return {"lines_checked": len(lines), "error_lines": len(errors), "by_pattern": counts,
            "last_errors": errors[-5:]}


def try_restart(name, wait):
    """Start one stopped container and report whether it came back."""
    log.warning("Auto-restart: starting %s", name)
    try:
        docker("start", name)
        time.sleep(wait)
        after = inspect(name)
        ok = after["status"] == "running"
        log.info("Auto-restart of %s %s (now %s)", name, "succeeded" if ok else "FAILED", after["status"])
        return {"attempted": True, "success": ok, "status_after": after["status"]}
    except MonitorError as e:
        log.error("Auto-restart of %s failed: %s", name, e)
        return {"attempted": True, "success": False, "error": str(e)}


def find_issues(c, args):
    issues = []
    if c["status"] != "running":
        issues.append({"severity": "critical", "message": f"container is {c['status']} (exit code {c['exit_code']})"})
    if c["health"] == "unhealthy":
        issues.append({"severity": "critical", "message": "health check reports unhealthy"})
    if c["stats"]:
        if c["stats"]["cpu_percent"] > args.cpu_threshold:
            issues.append({"severity": "warning", "message": f"CPU {c['stats']['cpu_percent']}% > {args.cpu_threshold}%"})
        if c["stats"]["memory_percent"] > args.mem_threshold:
            issues.append({"severity": "warning", "message": f"memory {c['stats']['memory_percent']}% > {args.mem_threshold}%"})
    if c["logs"]["error_lines"]:
        issues.append({"severity": "warning", "message": f"{c['logs']['error_lines']} error lines in last {args.tail} log lines"})
    if c["recovery"] and c["recovery"]["success"]:
        issues.append({"severity": "warning", "message": "was stopped, restarted automatically"})
    return issues


def check(args):
    names = list_containers(args.project)
    if not names:
        raise MonitorError(f"No containers found for compose project '{args.project}'")
    log.info("Checking %d containers in project '%s'", len(names), args.project)

    infos = [inspect(n) for n in names]
    recoveries = {}
    if args.auto_restart:
        for i in sorted(infos, key=lambda x: x["dependencies"]):     # databases/cache first, app last
            if i["status"] in STOPPED_STATES:
                if RESTARTS.get(i["name"], 0) >= args.max_restarts:
                    log.error("Giving up on %s: already restarted %d times", i["name"], args.max_restarts)
                    continue
                RESTARTS[i["name"]] = RESTARTS.get(i["name"], 0) + 1
                recoveries[i["name"]] = try_restart(i["name"], args.wait)
        infos = [inspect(n) for n in names]                  # refresh after restarts

    stats = get_stats([i["name"] for i in infos if i["status"] == "running"])
    containers = []
    for i in infos:
        c = dict(i, stats=stats.get(i["name"]), logs=analyze_logs(i["name"], args.tail),
                 recovery=recoveries.get(i["name"]))
        c["issues"] = find_issues(c, args)
        containers.append(c)

    severities = [x["severity"] for c in containers for x in c["issues"]]
    overall = "CRITICAL" if "critical" in severities else "WARNING" if severities else "HEALTHY"
    return {"generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "project": args.project, "overall_status": overall,
            "summary": {"total": len(containers),
                        "running": sum(c["status"] == "running" for c in containers),
                        "stopped": [c["name"] for c in containers if c["status"] != "running"],
                        "unhealthy": [c["name"] for c in containers if c["health"] == "unhealthy"],
                        "with_log_errors": [c["name"] for c in containers if c["logs"]["error_lines"]]},
            "containers": containers}


def run_once(args):
    report = check(args)
    out = Path(args.output or f"reports/health_{datetime.now():%Y%m%d_%H%M%S}.json")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, indent=2))
    for c in report["containers"]:
        s = c["stats"] or {}
        print(f"{c['name']:<30} {c['status']:<9} health={c['health']:<9} "
              f"cpu={s.get('cpu_percent', '-')}% mem={s.get('memory_percent', '-')}%")
        for x in c["issues"]:
            print(f"    [{x['severity']}] {x['message']}")
    log.info("Overall: %s | report: %s", report["overall_status"], out)
    return report["overall_status"]


def main():
    p = argparse.ArgumentParser(description="Frappe CRM Docker monitor")
    p.add_argument("--project", default="crm", help="compose project name (default: crm)")
    p.add_argument("--auto-restart", action="store_true", help="start stopped containers of the project")
    p.add_argument("--tail", type=int, default=200, help="log lines to analyze per container")
    p.add_argument("--cpu-threshold", type=float, default=80)
    p.add_argument("--mem-threshold", type=float, default=80)
    p.add_argument("--wait", type=float, default=5, help="seconds to wait after a restart")
    p.add_argument("--watch", type=float, metavar="SECONDS", help="keep checking every SECONDS until Ctrl+C")
    p.add_argument("--max-restarts", type=int, default=3, help="give up after this many restarts per container")
    p.add_argument("--output", help="report path (default: reports/health_<time>.json)")
    args = p.parse_args()
    try:
        while True:
            try:
                status = run_once(args)
            except MonitorError as e:
                if not args.watch:
                    raise
                log.error("%s (will retry)", e)
                status = None
            if not args.watch:
                return 0 if status == "HEALTHY" else 1
            time.sleep(args.watch)
            print()
    except KeyboardInterrupt:
        log.info("Stopped by user")
        return 0
    except MonitorError as e:
        log.error("%s", e)
        return 2
    except Exception as e:
        log.exception("Unexpected error: %s", e)
        return 2


if __name__ == "__main__":
    sys.exit(main())