
#!/usr/bin/env python3
"""
docker_monitor - Health monitoring and optional auto-recovery for Frappe CRM Docker containers.
 
Read-only by default. Uses the `docker` CLI (standard library only). It never touches
application code: it only inspects containers, reads their logs and, if you pass
--auto-restart, runs `docker start` on stopped containers inside the scope you selected.
"""
import argparse
import json
import logging
import os
import re
import shutil
import socket
import subprocess
import sys
import time
from datetime import datetime
from logging.handlers import RotatingFileHandler
from pathlib import Path
 
TOOL_VERSION = "1.0.0"
LOG = logging.getLogger("docker_monitor")
COMPOSE_PROJECT_LABEL = "com.docker.compose.project"
COMPOSE_SERVICE_LABEL = "com.docker.compose.service"
 
# Ordered: first match decides the category of a log line.
LOG_PATTERNS = [
    ("python_traceback", re.compile(r"Traceback \(most recent call last\)")),
    ("database_connection", re.compile(
        r"OperationalError|Can't connect to (MySQL|MariaDB)|Lost connection to MySQL|Too many connections", re.I)),
    ("redis_connection", re.compile(r"redis.*(connection refused|connectionerror|error \d+ connecting)", re.I)),
    ("out_of_memory", re.compile(r"out of memory|cannot allocate memory|Killed process|MemoryError|oom[- ]kill", re.I)),
    ("worker_timeout", re.compile(r"WORKER TIMEOUT|worker.*timed? ?out|SIGKILL", re.I)),
    ("connection_problem", re.compile(r"connection refused|connection reset|upstream timed out|no live upstreams", re.I)),
    ("permission_denied", re.compile(r"permission denied", re.I)),
    ("http_5xx", re.compile(r'HTTP/\d(\.\d)?"\s5\d{2}\b')),
    ("generic_error", re.compile(r"(?<![\w-])(error|critical|fatal)(?![\w-])", re.I)),
]
 
 
class ToolError(Exception):
    """Expected, user-facing failure."""
 
 
# --------------------------------------------------------------------------- #
# Logging / docker helpers
# --------------------------------------------------------------------------- #
def setup_logging(log_file: Path, verbose: bool) -> None:
    LOG.setLevel(logging.DEBUG)
    fmt = logging.Formatter("%(asctime)s | %(levelname)-8s | %(message)s")
    console = logging.StreamHandler(sys.stdout)
    console.setLevel(logging.DEBUG if verbose else logging.INFO)
    console.setFormatter(fmt)
    LOG.addHandler(console)
    log_file.parent.mkdir(parents=True, exist_ok=True)
    fh = RotatingFileHandler(log_file, maxBytes=5_000_000, backupCount=5, encoding="utf-8")
    fh.setLevel(logging.DEBUG)
    fh.setFormatter(fmt)
    LOG.addHandler(fh)
 
 
def docker(args, timeout=60, merge_stderr=False) -> str:
    """Run `docker <args>`; raise ToolError on failure."""
    cmd = ["docker"] + list(args)
    LOG.debug("exec: %s", " ".join(cmd))
    try:
        p = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout, errors="replace")
    except FileNotFoundError:
        raise ToolError("`docker` command not found. Install Docker or add it to PATH.")
    except subprocess.TimeoutExpired:
        raise ToolError(f"docker command timed out after {timeout}s: {' '.join(cmd)}")
    if p.returncode != 0:
        raise ToolError(f"docker command failed (exit {p.returncode}): {' '.join(cmd)}: {p.stderr.strip()}")
    return p.stdout + p.stderr if merge_stderr else p.stdout
 
 
def check_docker() -> str:
    try:
        return docker(["info", "--format", "{{.ServerVersion}}"], timeout=20).strip()
    except ToolError as e:
        raise ToolError(f"Cannot reach the Docker daemon: {e}")
 
 
def is_local_docker() -> bool:
    host = os.environ.get("DOCKER_HOST", "")
    return host == "" or host.startswith("unix://") or host.startswith("npipe://")
 
 
# --------------------------------------------------------------------------- #
# Collection
# --------------------------------------------------------------------------- #
def discover(args) -> list:
    """Return inspect dicts for containers inside the selected scope."""
    ids = set()
    if args.project:
        for proj in args.project:
            out = docker(["ps", "-a", "-q", "--no-trunc", "--filter", f"label={COMPOSE_PROJECT_LABEL}={proj}"])
            ids.update(out.split())
    else:
        ids.update(docker(["ps", "-a", "-q", "--no-trunc"]).split())
    if not ids:
        return []
    data = json.loads(docker(["inspect"] + sorted(ids)))
    name_re = re.compile(args.name_filter) if args.name_filter else None
    excl_re = re.compile(args.exclude) if args.exclude else None
    selected = []
    for c in data:
        name = c.get("Name", "").lstrip("/")
        if name_re and not name_re.search(name):
            continue
        if excl_re and excl_re.search(name):
            continue
        selected.append(c)
    return selected
 
 
def parse_percent(text) -> float:
    try:
        return float(str(text).strip().rstrip("%"))
    except ValueError:
        return None
 
 
def collect_stats(ids) -> dict:
    """{full_id_prefix: {...}} from `docker stats --no-stream` for running containers."""
    if not ids:
        return {}
    out = docker(["stats", "--no-stream", "--no-trunc", "--format", "{{json .}}"] + list(ids), timeout=120)
    stats = {}
    for line in out.splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            s = json.loads(line)
        except json.JSONDecodeError:
            LOG.warning("Unparseable stats line: %s", line[:200])
            continue
        stats[s.get("ID") or s.get("Container")] = s
    return stats
 
 
def analyze_logs(container_id: str, tail: int, since: str, max_samples: int) -> dict:
    result = {"lines_scanned": 0, "error_count": 0, "categories": {}, "samples": []}
    try:
        out = docker(["logs", "--tail", str(tail), "--since", since, container_id], timeout=60, merge_stderr=True)
    except ToolError as e:
        result["error"] = str(e)
        LOG.warning("Could not read logs for %s: %s", container_id[:12], e)
        return result
    for line in out.splitlines():
        result["lines_scanned"] += 1
        for cat, rx in LOG_PATTERNS:
            if rx.search(line):
                result["error_count"] += 1
                result["categories"][cat] = result["categories"].get(cat, 0) + 1
                if len(result["samples"]) < max_samples:
                    result["samples"].append({"category": cat, "line": line.strip()[:300]})
                break
    return result
 
 
# --------------------------------------------------------------------------- #
# Evaluation
# --------------------------------------------------------------------------- #
def evaluate(c: dict, stats: dict, args) -> dict:
    state = c.get("State", {})
    status = state.get("Status", "unknown")
    exit_code = state.get("ExitCode")
    health = (state.get("Health") or {}).get("Status")  # None if no healthcheck defined
    labels = c.get("Config", {}).get("Labels") or {}
    s = stats.get(c["Id"]) or stats.get(c["Id"][:12]) or {}
 
    cpu = parse_percent(s.get("CPUPerc")) if s else None
    mem = parse_percent(s.get("MemPerc")) if s else None
    info = {
        "name": c.get("Name", "").lstrip("/"),
        "id": c["Id"][:12],
        "full_id": c["Id"],
        "image": c.get("Config", {}).get("Image"),
        "compose_project": labels.get(COMPOSE_PROJECT_LABEL),
        "compose_service": labels.get(COMPOSE_SERVICE_LABEL),
        "status": status,
        "exit_code": exit_code,
        "health": health or "none",
        "restart_count": c.get("RestartCount", 0),
        "oom_killed": bool(state.get("OOMKilled")),
        "started_at": state.get("StartedAt"),
        "cpu_percent": cpu,
        "memory_percent": mem,
        "memory_usage": s.get("MemUsage") if s else None,
        "issues": [],
    }
 
    def issue(sev, code, msg):
        info["issues"].append({"severity": sev, "code": code, "message": msg})
 
    stopped = False
    if status == "running":
        pass
    elif status == "exited" and exit_code == 0 and args.oneshot_re.search(info["name"]):
        info["status_note"] = "completed (exit 0) one-shot job - not treated as stopped"
    elif status in ("exited", "dead"):
        stopped = True
        issue("critical", "STOPPED", f"container {status} with exit code {exit_code}")
    elif status == "restarting":
        issue("critical", "RESTART_LOOP", "container is restarting repeatedly")
    elif status in ("created", "paused"):
        issue("warning", status.upper(), f"container is {status}")
    else:
        issue("warning", "UNKNOWN_STATE", f"unexpected state '{status}'")
    info["stopped"] = stopped
 
    if info["oom_killed"]:
        issue("critical", "OOM_KILLED", "container was killed by the kernel for running out of memory")
    if health == "unhealthy":
        issue("critical", "UNHEALTHY", "healthcheck reports unhealthy")
    elif health == "starting":
        issue("warning", "HEALTH_STARTING", "healthcheck still in 'starting' state")
    if cpu is not None and cpu >= args.cpu_threshold:
        issue("warning", "HIGH_CPU", f"CPU {cpu:.1f}% >= {args.cpu_threshold}%")
    if mem is not None and mem >= args.mem_threshold:
        issue("warning", "HIGH_MEMORY", f"memory {mem:.1f}% >= {args.mem_threshold}%")
    if info["restart_count"] >= args.restart_threshold:
        issue("warning", "FREQUENT_RESTARTS", f"restart count {info['restart_count']} >= {args.restart_threshold}")
 
    la = analyze_logs(c["Id"], args.log_tail, args.log_since, args.max_samples)
    info["log_analysis"] = la
    if la["error_count"] > 0:
        issue("warning", "LOG_ERRORS", f"{la['error_count']} error line(s) in last {args.log_tail} lines "
              f"({', '.join(f'{k}={v}' for k, v in la['categories'].items())})")
 
    sevs = {i["severity"] for i in info["issues"]}
    info["severity"] = "critical" if "critical" in sevs else "warning" if "warning" in sevs else "ok"
    return info
 
 
# --------------------------------------------------------------------------- #
# Recovery
# --------------------------------------------------------------------------- #
class Recovery:
    def __init__(self, enabled, dry_run, max_restarts):
        self.enabled, self.dry_run, self.max_restarts = enabled, dry_run, max_restarts
        self.attempts = {}  # container id -> count (kept across watch cycles)
 
    def run(self, infos) -> list:
        actions = []
        if not self.enabled:
            return actions
        for i in infos:
            if not i["stopped"]:
                continue
            n = self.attempts.get(i["full_id"], 0)
            act = {"container": i["name"], "id": i["id"], "action": "docker start", "attempt": n + 1}
            if n >= self.max_restarts:
                act.update(result="skipped", detail=f"max restart attempts ({self.max_restarts}) reached")
                LOG.error("Not restarting %s: max attempts reached", i["name"])
            elif self.dry_run:
                act.update(result="dry-run", detail="would run docker start")
                LOG.info("[dry-run] would start %s", i["name"])
            else:
                self.attempts[i["full_id"]] = n + 1
                try:
                    LOG.warning("Starting stopped container %s", i["name"])
                    docker(["start", i["full_id"]], timeout=60)
                    time.sleep(3)
                    st = json.loads(docker(["inspect", i["full_id"]]))[0]["State"]
                    ok = st.get("Running", False)
                    act.update(result="recovered" if ok else "failed", detail=f"state after start: {st.get('Status')}")
                    (LOG.info if ok else LOG.error)("Recovery of %s: %s", i["name"], act["result"])
                except (ToolError, json.JSONDecodeError, KeyError, IndexError) as e:
                    act.update(result="failed", detail=str(e))
                    LOG.error("Recovery of %s failed: %s", i["name"], e)
            actions.append(act)
        return actions
 
 
# --------------------------------------------------------------------------- #
# Report
# --------------------------------------------------------------------------- #
def build_report(args, docker_version, infos, errors, actions) -> dict:
    crit = [i for i in infos if i["severity"] == "critical"]
    warn = [i for i in infos if i["severity"] == "warning"]
    overall = "CRITICAL" if crit else "WARNING" if warn else "HEALTHY"
    if not infos:
        overall = "NO_CONTAINERS"
    return {
        "report_version": 1,
        "tool_version": TOOL_VERSION,
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "host": socket.gethostname(),
        "docker_server_version": docker_version,
        "scope": {"projects": args.project or None, "name_filter": args.name_filter, "exclude": args.exclude},
        "thresholds": {"cpu_percent": args.cpu_threshold, "memory_percent": args.mem_threshold,
                       "restart_count": args.restart_threshold, "log_tail_lines": args.log_tail,
                       "log_since": args.log_since},
        "summary": {
            "overall_status": overall,
            "total_containers": len(infos),
            "running": sum(1 for i in infos if i["status"] == "running"),
            "stopped": [i["name"] for i in infos if i["stopped"]],
            "unhealthy": [i["name"] for i in infos if i["health"] == "unhealthy"],
            "with_log_errors": [i["name"] for i in infos if i["log_analysis"]["error_count"] > 0],
            "critical": len(crit),
            "warning": len(warn),
        },
        "containers": infos,
        "recovery": {"enabled": args.auto_restart, "dry_run": args.dry_run, "actions": actions},
        "collection_errors": errors,
    }
 
 
def run_cycle(args, recovery: Recovery) -> tuple:
    version = check_docker()
    errors = []
    try:
        raw = discover(args)
    except (json.JSONDecodeError, ToolError) as e:
        raise ToolError(f"Container discovery failed: {e}")
    LOG.info("Monitoring %d container(s)", len(raw))
 
    try:
        stats = collect_stats([c["Id"] for c in raw if c.get("State", {}).get("Running")])
    except ToolError as e:
        LOG.error("Could not collect CPU/memory stats: %s", e)
        errors.append({"stage": "stats", "error": str(e)})
        stats = {}
 
    infos = []
    for c in raw:
        try:
            infos.append(evaluate(c, stats, args))
        except Exception as e:  # one bad container must not abort the whole report
            LOG.exception("Failed to evaluate %s", c.get("Name"))
            errors.append({"stage": "evaluate", "container": c.get("Name"), "error": str(e)})
 
    actions = recovery.run(infos)
    report = build_report(args, version, infos, errors, actions)
 
    args.report_dir.mkdir(parents=True, exist_ok=True)
    path = args.report_dir / f"health_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    LOG.info("Report written: %s", path)
 
    s = report["summary"]
    LOG.info("Overall: %s | total=%d running=%d stopped=%d unhealthy=%d log_errors=%d",
             s["overall_status"], s["total_containers"], s["running"], len(s["stopped"]),
             len(s["unhealthy"]), len(s["with_log_errors"]))
    for i in infos:
        for it in i["issues"]:
            (LOG.error if it["severity"] == "critical" else LOG.warning)(
                "%s [%s] %s: %s", i["name"], it["severity"].upper(), it["code"], it["message"])
    rc = 0 if s["overall_status"] in ("HEALTHY",) else 1
    return rc, report
 
 
# --------------------------------------------------------------------------- #
# CLI
# --------------------------------------------------------------------------- #
def build_parser():
    p = argparse.ArgumentParser(prog="docker_monitor",
                                description="Monitor Frappe CRM Docker containers and optionally restart stopped ones")
    sc = p.add_argument_group("scope (at least one required, so shared containers are never touched by accident)")
    sc.add_argument("--project", action="append", help="Docker Compose project name (repeatable). See `docker compose ls`")
    sc.add_argument("--name-filter", help="Regex; only containers whose name matches")
    sc.add_argument("--exclude", help="Regex; skip containers whose name matches")
    th = p.add_argument_group("thresholds")
    th.add_argument("--cpu-threshold", type=float, default=80.0, help="CPU %% warning (default 80)")
    th.add_argument("--mem-threshold", type=float, default=85.0, help="Memory %% warning (default 85)")
    th.add_argument("--restart-threshold", type=int, default=3, help="Restart count warning (default 3)")
    lg = p.add_argument_group("log analysis")
    lg.add_argument("--log-tail", type=int, default=500, help="Lines per container to scan (default 500)")
    lg.add_argument("--log-since", default="1h", help="Only logs newer than this, e.g. 30m, 1h (default 1h)")
    lg.add_argument("--max-samples", type=int, default=5, help="Sample error lines per container (default 5)")
    sc.add_argument("--oneshot-pattern", default="configurator|create-site|init|setup|migrate",
                    help="Regex for one-shot job containers that are expected to exit 0 "
                         "(default: configurator|create-site|init|setup|migrate)")
    rc = p.add_argument_group("auto-recovery (off by default)")
    rc.add_argument("--auto-restart", action="store_true", help="Run `docker start` on stopped containers in scope")
    rc.add_argument("--dry-run", action="store_true", help="With --auto-restart: only report what would be started")
    rc.add_argument("--max-restarts", type=int, default=3, help="Max start attempts per container (default 3)")
    p.add_argument("--interval", type=int, help="Repeat every N seconds (default: run once)")
    p.add_argument("--report-dir", type=Path, default=Path("reports"))
    p.add_argument("--log-file", type=Path, default=Path("logs/docker_monitor.log"))
    p.add_argument("-v", "--verbose", action="store_true")
    return p
 
 
def main(argv=None) -> int:
    args = build_parser().parse_args(argv)
    setup_logging(args.log_file, args.verbose)
    try:
        if not args.project and not args.name_filter:
            raise ToolError("Select a scope with --project <compose-project> and/or --name-filter <regex>. "
                            "Run `docker compose ls` to see project names.")
        try:
            args.oneshot_re = re.compile(args.oneshot_pattern)
        except re.error as e:
            raise ToolError(f"Invalid --oneshot-pattern: {e}")
        if args.auto_restart and not args.dry_run and not is_local_docker():
            raise ToolError("Refusing --auto-restart: DOCKER_HOST points to a remote daemon. "
                            "Auto-recovery is for your local environment only.")
        if not shutil.which("docker"):
            raise ToolError("`docker` command not found. Install Docker or add it to PATH.")
        recovery = Recovery(args.auto_restart, args.dry_run, args.max_restarts)
        if not args.interval:
            return run_cycle(args, recovery)[0]
        LOG.info("Watch mode every %ds (Ctrl+C to stop)", args.interval)
        rc = 0
        while True:
            try:
                rc = run_cycle(args, recovery)[0]
            except ToolError as e:
                LOG.error("%s", e)
                rc = 2
            time.sleep(args.interval)
    except ToolError as e:
        LOG.error("%s", e)
        return 2
    except KeyboardInterrupt:
        LOG.info("Stopped by user")
        return 0
    except Exception:
        LOG.exception("Unexpected error")
        return 2
 
 
if __name__ == "__main__":
    sys.exit(main())