
# Frappe CRM Docker Monitoring & Auto-Recovery (Task 3)
 
Single-file Python tool (`docker_monitor.py`, standard library only) that uses the `docker` CLI to:
 
- Discover the Frappe CRM containers (by Docker Compose project and/or name regex)
- Check status, exit code, health status, restart count, OOM kills, CPU % and memory %
- Flag stopped, restarting and unhealthy containers
- Scan recent container logs for errors and group them by category
- Write a JSON health report
- Optionally restart stopped containers (`--auto-restart`, off by default)
It does not modify any Frappe CRM application code. By default it is read-only.
 
## Requirements
 
- Python 3.8+ (no pip packages)
- Docker CLI and a running local Docker daemon; your user must be allowed to run `docker`
## Setup
 
```bash
python3 docker_monitor.py --help
docker compose ls          # find your Frappe CRM compose project name
```
 
## Usage
 
A scope is mandatory (`--project` and/or `--name-filter`), so the tool never inspects or restarts containers you did not select.
 
```bash
# Read-only health check, one run
python3 docker_monitor.py --project frappe-crm
 
# Several projects / regex scope / exclude one-shot jobs
python3 docker_monitor.py --project frappe-crm --exclude 'configurator|create-site'
python3 docker_monitor.py --name-filter '^frappe-crm-'
 
# Custom thresholds and log window
python3 docker_monitor.py --project frappe-crm --cpu-threshold 70 --mem-threshold 80 --log-tail 1000 --log-since 30m
 
# Auto-recovery: preview first, then enable (local test environment only)
python3 docker_monitor.py --project frappe-crm --auto-restart --dry-run
python3 docker_monitor.py --project frappe-crm --auto-restart
 
# Continuous monitoring every 60 seconds
python3 docker_monitor.py --project frappe-crm --interval 60
```
 
Exit codes: `0` healthy, `1` warnings/critical found (or no containers matched), `2` tool failure (Docker unreachable, bad arguments).
 
## What counts as a problem
 
- **Critical:** container exited (any exit code, including a clean `docker stop`) or is dead, unless it matches the one-shot pattern; restarting in a loop; health status `unhealthy`; OOM-killed
- **Warning:** health `starting`; created/paused; CPU or memory above threshold (defaults 80% / 85%); restart count at or above 3; error lines found in logs
- **Not a problem:** a container that exited with code 0 **and** whose name matches `--oneshot-pattern` (default `configurator|create-site|init|setup|migrate`). These are finished one-shot jobs, for example frappe_docker's configurator and site-creation containers, and are neither reported as stopped nor restarted. Change the pattern if your one-shot containers are named differently.
Log lines are classified by first matching category: python_traceback, database_connection, redis_connection, out_of_memory, worker_timeout, connection_problem, permission_denied, http_5xx, generic_error. The report keeps up to 5 sample lines per container (300 characters each).
 
## Auto-recovery safety rules
 
- Off unless `--auto-restart` is passed; `--dry-run` shows what would happen
- Only acts on containers inside the selected scope and only on stopped ones (exited or dead, excluding one-shot jobs); it runs `docker start`, never `docker rm`, `docker stop` or `docker restart` on running containers
- Maximum 3 start attempts per container (`--max-restarts`)
- Refuses to run if `DOCKER_HOST` points to a remote daemon
- After each start it re-inspects the container and records `recovered` or `failed` in the report
## Report
 
Written to `reports/health_report_<timestamp>.json`:
 
- `summary`: overall status (`HEALTHY`, `WARNING`, `CRITICAL`, `NO_CONTAINERS`), counts, stopped/unhealthy/log-error lists
- `containers[]`: name, id, image, compose service, status, exit code, health, restart count, CPU %, memory %, issues, `log_analysis`
- `recovery`: whether enabled, dry-run flag, and every action with its result
- `collection_errors`: anything the tool could not collect (the run continues)
The summary reflects container state at detection time; recovery results are in `recovery.actions`.
 
## Logging and error handling
 
Console plus rotating file `logs/docker_monitor.log` (`-v` for debug). Docker not installed, daemon unreachable, command timeouts, unreadable logs and failed stats are handled and logged; a problem with one container does not abort the report.
 
## Sample reports
 
Real reports from my own local run are in `sample_reports/`.
 
## Limitations
 
- Containers without a Docker healthcheck show health `none`
- CPU/memory come from a single `docker stats --no-stream` sample, so CPU can be a momentary value
- Log analysis is pattern based and can miss unusual error formats or count harmless lines containing the word "error"