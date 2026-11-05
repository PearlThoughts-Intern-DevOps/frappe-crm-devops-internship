# Docker Monitoring and Auto-Recovery Tool

A Python-based monitoring tool for Frappe CRM Docker containers.

## Features
- Discovers configured Frappe CRM containers.
- Checks container running status and Docker health status.
- Collects CPU and memory usage.
- Collects recent container logs and searches for configured error patterns.
- Generates a JSON system health report.
- Records monitoring activity and exceptions in a log file.
- Supports optional auto-recovery for allowlisted containers.

## Requirements
- Python 3.10+
- Docker CLI
- Docker daemon running and accessible

No third-party Python packages are required.

## Usage

Run normal monitoring:

    python3 monitor.py

Run optional auto-recovery:

    python3 monitor.py --auto-restart

## Configuration

Edit config.json to configure container filters, log patterns, report paths and the auto-restart allowlist.

Auto-recovery is restricted to the explicitly allowlisted disposable test container. Do not add shared CRM containers to this allowlist.

## Output
- reports/system-health-report.json
- logs/monitoring.log

The tool does not modify Frappe CRM application source code.
