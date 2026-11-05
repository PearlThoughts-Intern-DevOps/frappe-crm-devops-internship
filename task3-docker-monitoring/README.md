\# Docker Container Monitoring and Auto-Recovery Tool



\## Project Overview



This project implements a Python-based Docker Container Monitoring and Auto-Recovery Tool for Frappe CRM.



It uses the Docker SDK for Python to monitor container status, health, CPU and memory utilization, and container logs. It generates a JSON health report and provides an optional auto-restart feature for approved Frappe CRM containers.



\## Features



\- Monitor Docker containers and their running status.

\- Collect container health information.

\- Monitor CPU and memory utilization.

\- Detect stopped and unhealthy containers.

\- Scan the last 100 log lines for common error indicators.

\- Generate a JSON system health report.

\- Maintain application logs.

\- Optional auto-restart for approved stopped Frappe CRM containers.

\- Exception handling for Docker API and monitoring errors.



\## Technologies Used



| Technology | Purpose |

|---|---|

| Python | Monitoring and recovery logic |

| Docker | Container management |

| Docker SDK for Python | Communication with Docker Engine |

| JSON | Health report generation |

| Logging | Application event and error tracking |

| PowerShell | Running commands on Windows |



\## Project Structure



```text

task3-docker-monitoring/

│

├── docker\_monitor.py

├── requirements.txt

├── README.md

│

├── reports/

│   └── health\_report.json

│

└── logs/

&#x20;   └── monitoring.log

```



\## Prerequisites



\- Python 3.12 or compatible version

\- Docker Desktop

\- Docker Engine running

\- PowerShell

\- Git



\## Installation



Navigate to the project directory:



```powershell

cd task3-docker-monitoring

```



Install the Python dependency:



```powershell

pip install -r requirements.txt

```



Verify Docker connectivity:



```powershell

docker version

```



\## Usage



\### 1. Normal Monitoring



Run the monitoring script:



```powershell

python .\\docker\_monitor.py

```



This collects container information and generates:



```text

reports/health\_report.json

```



\### 2. Enable Optional Auto-Recovery



Run:



```powershell

python .\\docker\_monitor.py --auto-restart

```



The recovery feature attempts to restart stopped containers whose names are included in the approved recovery list.



Auto-recovery is disabled by default.



\### 3. View the JSON Report



```powershell

Get-Content .\\reports\\health\_report.json

```



\### 4. View Monitoring Logs



```powershell

Get-Content .\\logs\\monitoring.log

```



\## Health Report Information



The JSON report contains:



\- Report generation timestamp

\- Total container count

\- Running and stopped container counts

\- Unhealthy container count

\- Frappe CRM container details

\- Container image and status

\- CPU utilization

\- Memory usage and utilization

\- Container restart count

\- Log scanning results

\- Recovery status



CPU and memory values are unavailable for stopped containers and are represented as null.



\## Auto-Recovery Safety



The recovery feature is optional and disabled during normal monitoring.



Only containers listed in `RECOVERY\_CONTAINERS` are eligible for automatic recovery:



\- crm-frappe-1

\- crm-mariadb-1

\- crm-redis-1



Other Docker project containers and frappe-inspect are excluded from automatic recovery.



\## Testing Performed



1\. Verified Docker SDK connectivity.

2\. Tested container status monitoring.

3\. Tested CPU and memory collection using a temporary Redis container.

4\. Tested stopped-container detection.

5\. Verified JSON health report generation.

6\. Tested log collection.

7\. Tested optional auto-recovery using a temporary Redis container.

8\. Verified that normal monitoring does not trigger recovery.

9\. Verified cleanup of temporary test containers.



\## Conclusion



The project demonstrates Docker container monitoring, resource utilization tracking, log analysis, JSON reporting, Python exception handling, and optional container recovery.



It provides a foundation for monitoring Docker-based Frappe CRM environments.



