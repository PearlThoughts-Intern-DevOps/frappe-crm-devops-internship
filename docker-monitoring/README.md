
# Docker Monitoring and Auto-Recovery Tool

A Python-based monitoring and recovery tool for the local Frappe CRM Docker environment.

## Features

- Monitors the three Frappe CRM services: Frappe, MariaDB, and Redis.
- Checks container status, restart count, exit code, and OOM-kill status.
- Collects health-check information when Docker health checks are configured.
- Collects CPU and memory statistics for running containers.
- Reads recent container logs and identifies configurable error keywords.
- Detects stopped, unhealthy, and missing containers.
- Generates timestamped JSON health reports.
- Maintains application logs.
- Supports optional, allowlist-protected container recovery.

## Project Scope

The monitor is restricted to the local Docker Compose project named `crm`.

It verifies the expected containers and their Docker Compose project and service labels:

| Container | Service |
|---|---|
| `crm-frappe-1` | frappe |
| `crm-mariadb-1` | mariadb |
| `crm-redis-1` | redis |

The tool does not modify Frappe application code or Docker volumes.

## Requirements

- Python 3.10 or later
- Docker Desktop or Docker Engine
- Docker CLI accessible from the terminal
- Permission to inspect and read logs from Docker containers

The tool uses Python's standard library. No third-party Python packages are required.

## Project Structure

```text
docker-monitoring/
├── monitor.py
├── test_monitor.py
├── config.json
├── README.md
├── logs/
│   └── .gitkeep
└── reports/
    └── .gitkeep
```

Generated logs and reports are excluded from Git.

## Configuration

The `config.json` file controls log collection and recovery permissions.

Important settings:

- `log_lines`: Number of recent log lines collected per container.
- `keywords`: Keywords used to identify possible log errors.
- `restart_allowlist`: Exact container names explicitly approved for recovery.

The restart allowlist is empty by default. This prevents automatic recovery unless a container has been explicitly approved.

The monitored project and expected services are defined in the monitoring script.

## Running the Monitor

Run a single monitoring cycle from the repository root:

```bash
python docker-monitoring/monitor.py
```

Run continuous monitoring with a 30-second interval:

```bash
python docker-monitoring/monitor.py --interval 30
```

## Auto-Recovery

Automatic recovery is disabled unless the `--auto-restart` option is supplied.

Before enabling it, explicitly add the intended local container name to `restart_allowlist` in `config.json`.

Example:

```json
"restart_allowlist": ["crm-redis-1"]
```

Then run:

```bash
python docker-monitoring/monitor.py --auto-restart
```

Only allowlisted, stopped or created containers are eligible for recovery. The tool re-inspects the container after attempting to start it.

Use auto-recovery only in an authorized local environment. Do not enable it against shared or production infrastructure.

## Health Reports

Each monitoring cycle generates a JSON report in:

```text
docker-monitoring/reports/
```

Reports include:

- Overall system health
- Expected and monitored container counts
- Missing containers
- Container status and health information
- CPU and memory usage, when available
- Restart and exit information
- Detected log errors
- Recovery actions and outcomes

The overall health status is classified as:

- `healthy`: All monitored containers are running and no critical issues are detected.
- `degraded`: Monitoring identifies a condition that needs attention but is not classified as critical.
- `critical`: A required container is missing, stopped, unhealthy, or cannot be inspected.

A container without a configured Docker health check is reported as `not_configured`.

## Running Tests

Run the automated test suite from the repository root:

```bash
python -m unittest discover -s docker-monitoring -p "test_*.py" -v
```

The tests use mocked Docker interactions to validate discovery, recovery safeguards, post-recovery inspection, and health classification without starting or modifying real containers.

## Current Local Test Result

The monitoring tool successfully discovered all three expected CRM containers.

At the time of the test:

- Expected containers: 3
- Monitored containers: 3
- Running containers: 0
- Stopped containers: 3
- Missing containers: 0
- Inspection errors: 0
- Overall health: `critical`

The critical status accurately reflects the stopped state of the local containers. It does not indicate that the monitoring script failed.
