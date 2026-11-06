# Docker Monitoring and Automation for Frappe CRM

## Project Overview

This project monitors Docker containers used by the Frappe CRM application through a Python script and the Docker SDK.

The monitoring script collects container information, checks container status and health, monitors CPU and memory usage, analyzes container logs, and generates a JSON health report.

It also includes a recovery test that demonstrates how a stopped disposable Docker container can be restarted automatically.

**Important:** This project does not modify the original Frappe CRM application code.

## Project Structure

```text
docker-automation/
│
├── .venv/                  # Python virtual environment
├── logs/                   # Monitoring logs
├── reports/                # Generated JSON reports
├── monitor.py              # Main monitoring script
├── requirements.txt        # Python dependencies
└── README.md               # Project documentation
```

## Technologies Used

- Python
- Docker
- Docker SDK for Python
- Docker Engine
- JSON

## Prerequisites

Before running the project, make sure you have:

1. Python installed.
2. Docker Desktop installed and running.
3. Frappe CRM Docker containers running.
4. Access to the Docker Engine.

## Installation and Setup

### 1. Open the project directory

Open PowerShell in the `docker-automation` folder.

### 2. Create a virtual environment

```powershell
py -m venv .venv
```

### 3. Activate the virtual environment

```powershell
.\.venv\Scripts\Activate.ps1
```

### 4. Install dependencies

```powershell
python -m pip install -r requirements.txt
```

The `requirements.txt` file contains the Docker SDK for Python, which allows the monitoring script to communicate with Docker.

## Configuration

Set the Docker Compose project name before running the monitoring script.

For this project, the Compose project name is `crm`.

Run this command in PowerShell:

```powershell
$env:FRAPPE_COMPOSE_PROJECT = "crm"
```

To verify the value:

```powershell
echo $env:FRAPPE_COMPOSE_PROJECT
```

**Note:** This environment variable applies to the current PowerShell session. Set it again when opening a new session.

## Running the Monitoring Script

Run the following command:

```powershell
python monitor.py
```

The script connects to Docker and monitors the containers belonging to the configured Frappe CRM Compose project.

### Monitoring Features

The script is designed to:

- Check Docker container status.
- Identify stopped or unhealthy containers.
- Collect CPU usage information.
- Collect memory usage information.
- Analyze container logs.
- Generate a JSON health report.
- Record monitoring activity and errors in log files.

## Automatic Recovery Test

The project includes a recovery test using a disposable Alpine Linux container.

Run:

```powershell
python monitor.py --test-recovery
```

The test:

1. Creates a temporary Docker container.
2. Stops the container to simulate a failure.
3. Attempts to restart it.
4. Checks whether recovery was successful.
5. Removes the temporary test container.

A successful test displays:

```text
AUTO-RECOVERY TEST PASSED
```

This test does not require restarting shared Frappe CRM containers.

## Generated Reports and Logs

The monitoring script generates a JSON health report at:

```text
reports/health_report.json
```

Monitoring logs are stored in:

```text
logs/
```

The JSON report provides information about the monitoring results and container health.

## Safety Precautions

- Do not modify the original Frappe CRM application code.
- Do not stop, restart, or modify shared Frappe CRM containers.
- Test recovery only with disposable containers in your local environment.
- Use the monitoring script to inspect container information without disrupting shared services.

## Expected Outcome

After running the monitoring script, the project should:

- Connect successfully to Docker.
- Identify the configured Frappe CRM containers.
- Collect container health and resource information.
- Analyze container logs.
- Generate a JSON health report.
- Record monitoring activity and errors.

The recovery test should demonstrate successful automatic recovery using a disposable test container.

## Author

Docker Monitoring and Automation for Frappe CRM

**Project:** DevOps Internship Task