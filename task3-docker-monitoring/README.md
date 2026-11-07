# Docker Container Monitoring and Auto-Recovery Tool

A Python-based monitoring tool for Docker containers used by a local **Frappe CRM** environment. It collects container health and resource information, scans recent logs for common error indicators, and creates a JSON health report. An optional auto-recovery mode can restart approved containers when they are stopped.

---

## 1. Project Overview

Docker containers run the application and its supporting services. If a container stops or becomes unhealthy, the application may become unavailable or some functions may not work as expected.

This project provides a lightweight way to inspect Docker containers using a Python script.

The tool uses the **Docker SDK for Python** to communicate with Docker Engine. It gathers information such as:

- Container name, image, and current status
- Health information, when available
- CPU and memory utilization
- Container restart count
- Recent container logs
- Recovery status, when auto-recovery is enabled

The collected information is written to a JSON health report. The tool also maintains an application log for monitoring events and errors.

## 2. Project Objectives

1. Monitor the status of Docker containers used by Frappe CRM.
2. Identify containers that are stopped or unhealthy.
3. Collect CPU and memory utilization information.
4. Inspect recent logs for common error indicators.
5. Generate a structured JSON report for review.
6. Record monitoring activity and errors.
7. Provide an optional, controlled restart mechanism for approved containers.

## 3. Key Features

| Feature | Explanation |
|---|---|
| Container status monitoring | Checks whether Docker containers are running or stopped. |
| Health information | Collects container health information when Docker provides it. |
| CPU monitoring | Collects CPU utilization information for running containers. |
| Memory monitoring | Collects memory usage and utilization information for running containers. |
| Stopped/unhealthy detection | Identifies containers that are stopped or reported as unhealthy. |
| Log scanning | Checks the last 100 lines of container logs for common error indicators. |
| JSON health report | Saves monitoring results in `reports/health_report.json`. |
| Application logging | Records monitoring events and errors in `logs/monitoring.log`. |
| Optional auto-recovery | Attempts to restart stopped containers included in an approved recovery list. |
| Exception handling | Handles Docker API and monitoring errors. |

## 4. Technologies Used

| Technology | Purpose |
|---|---|
| **Python** | Implements the monitoring, reporting, and recovery logic. |
| **Docker** | Runs Frappe CRM and its supporting services in containers. |
| **Docker SDK for Python** | Allows the Python script to communicate with Docker Engine and inspect/manage containers. |
| **JSON** | Stores the generated health report in a structured format. |
| **Python Logging** | Records application events, warnings, and errors. |
| **PowerShell** | Provides the Windows command-line environment used to run the project. |

### How the components work together

1. The Python monitoring script uses the Docker SDK to connect to Docker Engine.
2. Docker Engine provides container status, health, resource, restart, and log information.
3. The script processes the collected information and checks for stopped or unhealthy containers.
4. Monitoring results are written to a JSON report.
5. Monitoring events and errors are recorded in the application log.
6. If auto-restart is enabled, the script can attempt recovery for stopped containers on its approved list.

## 5. Project Structure

```text
task3-docker-monitoring/
│
├── docker_monitor.py
├── requirements.txt
├── README.md
│
├── reports/
│   └── health_report.json
│
└── logs/
    └── monitoring.log
```

| File or directory | Explanation |
|---|---|
| `docker_monitor.py` | Main Python script for container monitoring, report generation, logging, and optional recovery. |
| `requirements.txt` | Lists the Python dependencies required by the project. |
| `README.md` | Documents the project, setup, execution, and expected outputs. |
| `reports/` | Stores generated health reports. |
| `reports/health_report.json` | JSON output containing the latest monitoring results. |
| `logs/` | Stores application log files. |
| `logs/monitoring.log` | Records monitoring events and errors. |

## 6. Prerequisites

- Python 3.12 or a compatible version
- Docker Desktop installed
- Docker Engine running
- PowerShell
- Git

Docker Desktop must be running so that the Python Docker SDK can communicate with Docker Engine.

## 7. Installation and Setup

### Step 1: Open the project directory

In PowerShell, navigate to the project folder:

```powershell
cd task3-docker-monitoring
```

### Step 2: Install the Python dependencies

```powershell
pip install -r requirements.txt
```

This installs the packages listed in `requirements.txt`, including the Docker SDK dependency specified by the project.

### Step 3: Verify Docker connectivity

```powershell
docker version
```

Confirm that Docker client and server information is displayed before running the monitoring script.

## 8. Running the Tool

### 8.1 Normal monitoring

```powershell
python .\docker_monitor.py
```

In normal mode, the tool collects container information, checks for stopped or unhealthy containers, scans recent logs, and generates the health report.

The report is saved to:

```text
reports/health_report.json
```

Normal monitoring does not enable automatic restart.

### 8.2 Enable optional auto-recovery

```powershell
python .\docker_monitor.py --auto-restart
```

This enables the optional recovery mode. The script attempts to restart stopped containers only when their names are included in the approved recovery list.

Auto-recovery is disabled by default. Use this option only when you intend to allow the tool to restart eligible containers.

### 8.3 View the JSON health report

```powershell
Get-Content .\reports\health_report.json
```

The report provides a structured record of the monitoring results.

### 8.4 View the application log

```powershell
Get-Content .\logs\monitoring.log
```

The log helps review monitoring activity and investigate errors encountered during execution.

## 9. Understanding the Health Report

The JSON report contains:

| Information | Explanation |
|---|---|
| Report generation timestamp | Indicates when the report was generated. |
| Total container count | Number of containers included in the monitoring results. |
| Running container count | Number of containers reported as running. |
| Stopped container count | Number of containers reported as stopped. |
| Unhealthy container count | Number of containers reported as unhealthy. |
| Frappe CRM container details | Monitoring details for the relevant Frappe CRM containers. |
| Container image and status | Identifies the image used by a container and its current status. |
| CPU utilization | Reports CPU utilization information when available. |
| Memory usage and utilization | Reports memory consumption information when available. |
| Container restart count | Shows the restart count collected for the container. |
| Log scanning results | Records the results of scanning recent container logs. |
| Recovery status | Records recovery information when the recovery feature is used. |

**Note:** CPU and memory values are unavailable for stopped containers and are represented as `null` in the report.

## 10. Auto-Recovery and Safety Controls

The auto-recovery feature is optional. It is disabled during normal monitoring and must be explicitly enabled:

```powershell
python .\docker_monitor.py --auto-restart
```

Only containers included in `RECOVERY_CONTAINERS` are eligible for automatic recovery:

- `crm-frappe-1`
- `crm-mariadb-1`
- `crm-redis-1`

Other Docker project containers and `frappe-inspect` are excluded from automatic recovery.

### Why use an approved recovery list?

A Docker environment may contain containers used for development, testing, inspection, or other purposes. Restarting every stopped container automatically may cause unwanted interruptions.

The approved list limits recovery attempts to the specified Frappe CRM services.

**Operational note:** Restarting a database or application container can interrupt active work. Review the approved list and understand the impact before enabling auto-recovery, especially outside a local development environment.

## 11. Testing Performed

| No. | Test | What it verifies |
|---:|---|---|
| 1 | Docker SDK connectivity | Confirms that the Python tool can communicate with Docker. |
| 2 | Container status monitoring | Checks that container states can be collected. |
| 3 | CPU and memory collection using a temporary Redis container | Checks resource information collection for a running test container. |
| 4 | Stopped-container detection | Checks that stopped containers can be identified. |
| 5 | JSON health report generation | Confirms that monitoring results are written to the report file. |
| 6 | Log collection | Checks that container logs can be retrieved and scanned. |
| 7 | Optional auto-recovery using a temporary Redis container | Tests the recovery path with a temporary test container. |
| 8 | Normal monitoring without recovery | Verifies that normal execution does not trigger automatic recovery. |
| 9 | Temporary test-container cleanup | Confirms that temporary test containers were cleaned up after testing. |

## 12. Troubleshooting Notes

### Docker Engine is not available

**Possible reason:** Docker Desktop is not running, or Docker Engine is not ready.

Check:

```powershell
docker version
```

Start Docker Desktop, wait until the Engine is running, and retry.

### Python dependency is missing

Install the project dependencies:

```powershell
pip install -r requirements.txt
```

### Health report is not present

Check whether the reports directory contains the report:

```powershell
Get-ChildItem .\reports
```

Run the monitoring script again and review the terminal output and application log:

```powershell
Get-Content .\logs\monitoring.log
```

These are general checks based on the documented project files and commands. Use the actual error output to determine the specific cause.

## 13. Important Commands – Quick Reference

| Command | Purpose |
|---|---|
| `cd task3-docker-monitoring` | Opens the project directory. |
| `pip install -r requirements.txt` | Installs the Python dependencies. |
| `docker version` | Checks Docker client and Engine availability. |
| `python .\docker_monitor.py` | Runs normal monitoring. |
| `python .\docker_monitor.py --auto-restart` | Runs monitoring with optional auto-recovery enabled. |
| `Get-Content .\reports\health_report.json` | Displays the JSON health report. |
| `Get-Content .\logs\monitoring.log` | Displays the application log. |

## 14. Key Learnings

This project provided practical experience with:

- Using the Docker SDK for Python to interact with Docker Engine.
- Collecting container status and health information programmatically.
- Monitoring CPU and memory utilization.
- Detecting stopped and unhealthy containers.
- Retrieving and scanning recent container logs.
- Generating structured JSON output for monitoring results.
- Using Python logging to record application events and errors.
- Handling Docker API and monitoring exceptions.
- Implementing an optional recovery mechanism with an approved container list.
- Testing monitoring and recovery behavior with a temporary container.

## 15. Conclusion

The Docker Container Monitoring and Auto-Recovery Tool demonstrates how Python can be used to monitor a Docker-based Frappe CRM environment.

It brings together container status checks, health information, resource monitoring, log scanning, JSON reporting, application logging, exception handling, and optional controlled recovery.

The project provides a practical foundation for understanding container monitoring and basic recovery automation in a local Docker environment.

---

**Project:** Docker Container Monitoring and Auto-Recovery Tool  
**Application environment:** Frappe CRM  
**Primary language:** Python  
**Container platform:** Docker
