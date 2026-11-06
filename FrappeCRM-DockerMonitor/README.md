# FrappeCRM Docker Container Monitoring & Auto-Recovery Tool

An enterprise-grade, zero-dependency Python observability and self-healing watchdog for the Frappe CRM Docker stack (`crm-frappe-1`, `crm-mariadb-1`, `crm-redis-1`).

---

## Architecture Overview

```
FrappeCRM-DockerMonitor/
├── dockermonitor.py                 # Top-level executable CLI entry point
├── DockerMonitor/
│   ├── config.py                   # MonitorConfig, thresholds & directory setup
│   ├── exceptions.py               # Custom exception hierarchy
│   ├── logger.py                   # Colorized console + rotating file handler
│   ├── models.py                   # Typed dataclasses (telemetry, state, reports)
│   ├── engine.py                   # Unix Socket HTTP client + Docker CLI fallback
│   ├── state.py                    # Persistent state manager (cursors & circuit breaker)
│   ├── collector.py                # Telemetry & cgroup math collector + liveness probes
│   ├── analyzer.py                 # Multi-line log folder & regex error classifier
│   ├── recovery.py                 # Topological auto-recovery & circuit breaker engine
│   ├── reporter.py                 # JSON report generator, retention pruner & ANSI table
│   ├── cli.py                      # Argument parser, signal handling, exit code router
│   └── tests/
│       └── test_docker_monitor.py  # Unit test suite (unittest)
├── reports/                        # JSON health audit reports & latest_health_report.json
├── state/                          # Persistent state (monitor_state.json)
└── logs/                           # Rotating execution log (docker_monitor.log)
```

---

## Key Features

1. **Zero External Dependencies**:
   Communicates directly with `/var/run/docker.sock` via Python standard library `http.client` and `socket.AF_UNIX` with automatic fallback to Docker CLI subprocess. Runs out of the box on Python 3.12 without `pip`.
2. **Accurate Linux Cgroup Resource Telemetry**:
   Calculates true container memory by subtracting page cache (`usage - inactive_file`), preventing false alarms.
3. **Active Application-Layer Liveness Probes**:
   Detects silent deadlocks where a container is `running` with health `none`:
   - **MariaDB**: `mariadb-admin ping -uroot -p123`
   - **Redis**: `redis-cli ping` (verifies `PONG`)
   - **Frappe**: HTTP check to `/api/method/ping`
4. **Intelligent Multi-Line Log Parser**:
   Folds 20+ line Python tracebacks into a single logical event to avoid duplicate alert cascades, and tracks `--since` cursors across runs.
5. **Stateful Circuit Breaker & Topological Auto-Recovery**:
   - Opt-in via `--auto-restart` with `--dry-run` simulation mode.
   - Wakes up Tier 1 (MariaDB, Redis) before Tier 2 (Frappe).
   - Trips circuit breaker after 3 consecutive failures to prevent restart loops.
6. **Standardized Linux SRE Exit Codes**:
   - `0`: Cluster `HEALTHY`
   - `1`: Cluster `DEGRADED` (or auto-recovered)
   - `2`: Cluster `CRITICAL`
   - `3`: Fatal / Daemon Error

---

## CLI Usage & Commands

### 1. One-Shot Cluster Health Audit
```bash
python3 FrappeCRM-DockerMonitor/dockermonitor.py --check
```

### 2. Generate JSON Report
```bash
python3 FrappeCRM-DockerMonitor/dockermonitor.py --check --report
```
*Saves timestamped report in `reports/health_report_YYYYMMDD_HHMMSS.json` and updates `reports/latest_health_report.json`.*

### 3. Dry-Run Recovery Simulation (Safe)
```bash
python3 FrappeCRM-DockerMonitor/dockermonitor.py --check --auto-restart --dry-run
```

### 4. Live Auto-Recovery for Stopped / Unhealthy Containers
```bash
python3 FrappeCRM-DockerMonitor/dockermonitor.py --check --auto-restart --report
```

### 5. Continuous Watch Daemon Mode (30s interval)
```bash
python3 FrappeCRM-DockerMonitor/dockermonitor.py --watch --interval 30
```

### 6. Raw JSON Output for Piping (jq, Datadog, Nagios)
```bash
python3 FrappeCRM-DockerMonitor/dockermonitor.py --json | jq .cluster_status
```

---

## Running Unit Tests

```bash
PYTHONPATH=FrappeCRM-DockerMonitor python3 -m unittest discover -s FrappeCRM-DockerMonitor/DockerMonitor/tests -v
```
