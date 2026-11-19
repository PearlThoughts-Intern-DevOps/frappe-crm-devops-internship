# Frappe CRM Docker Monitor

A Python tool (`monitor.py`) that monitors the Docker containers of the Frappe CRM compose project. It checks status, health, CPU and memory, finds stopped or unhealthy containers, scans their logs for errors, writes a JSON health report, and can optionally restart stopped containers. It doesn't modify the CRM code.

## Requirements
Python 3.9+ (standard library only) and Docker. The CRM stack must be running through Docker Compose (default project name `crm`).

## Usage
```bash
python3 monitor.py                              # one check, writes reports/health_<time>.json
python3 monitor.py --auto-restart               # also start stopped containers
python3 monitor.py --watch 30 --auto-restart    # keep checking every 30s until Ctrl+C
python3 monitor.py --project crm-restore-test   # monitor another compose project
```

To keep your terminal free in watch mode, run it in the background and stop it later:
```bash
nohup python3 monitor.py --watch 30 --auto-restart --output reports/health_latest.json > /dev/null 2>&1 &
pkill -f monitor.py
```

| Option | Meaning |
|---|---|
| `--project` | compose project to monitor (default `crm`) |
| `--auto-restart` | start containers that are stopped (exited or dead) |
| `--watch SECONDS` | repeat the check every SECONDS until Ctrl+C |
| `--max-restarts N` | give up on a container after N restarts (default 3) |
| `--tail N` | log lines to analyze per container (default 200) |
| `--cpu-threshold`, `--mem-threshold` | warn above this percentage (default 80) |
| `--wait SECONDS` | pause after a restart before re-checking (default 5) |
| `--output FILE` | report path (default `reports/health_<time>.json`) |

Exit codes: 0 = healthy, 1 = warning or critical, 2 = the tool itself failed (for example Docker not running).

## What it checks
| Check | How |
|---|---|
| Containers | `docker ps -a` filtered by the compose project label, so only this project's containers are ever looked at |
| Status and health | `docker inspect` (status, health check result, exit code, restart count) |
| CPU and memory | `docker stats --no-stream` |
| Log errors | `docker logs --tail N`, searching for error, exception, traceback, critical, fatal, refused. Lines a service labels `[Warning]` and known startup config lines are ignored |
| Auto-restart | `docker start` on stopped containers, starting the ones others depend on (database, cache) first and the app last, then re-checks the status |

Severity: a stopped or unhealthy container is **critical**. High CPU or memory, errors in the logs, and "was restarted automatically" are **warnings**. The overall status is `CRITICAL`, `WARNING` or `HEALTHY`.

## JSON report
Top level: `generated_at`, `project`, `overall_status`, `summary` (total, running, stopped, unhealthy, with_log_errors) and `containers`. Each container has `status`, `health`, `exit_code`, `restart_count`, `dependencies`, `stats` (cpu_percent, memory_percent, memory_usage), `logs` (error counts and the last error lines), `recovery` (restart attempt result) and `issues`. Examples are in `sample_reports/`.

## Safety
- Only containers of the chosen compose project are ever inspected or restarted.
- Nothing is restarted unless `--auto-restart` is given, and only stopped containers are started.
- A container that keeps failing is restarted at most `--max-restarts` times, then reported as critical.
- Auto-recovery was tested only on my own local stack.

## Logging and errors
Log lines go to the screen and to `monitor.log`. Problems with Docker (not installed, daemon not running, no containers found, timeouts) are reported as one clear message with exit code 2. In `--watch` mode, an error in one check is logged and the next check retries, so one failure doesn't stop the monitor.

## Limitations
- It recovers containers that are stopped or crashed. A container that was removed (for example by `docker compose down`) is no longer listed and needs `docker compose up`.
- Restarting a container keeps its data. MariaDB's data is in a Docker volume and survives a restart.
- Log analysis looks at the last N lines regardless of age, so errors from an earlier incident can stay flagged until newer output pushes them out.
- The restart counter lives in memory, so it resets when the monitor itself restarts.
- Running containers that are unhealthy are reported but not restarted. The Frappe container has no health check, so its health shows as `none`.
