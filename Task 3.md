# Task 3: Docker Monitoring and Auto-Recovery for Frappe CRM

**Prepared by:** Hanumanth572  
**Branch for PR:** `task3-hanumanth572-pr`  
**Status:** Implementation and local validation complete; pull request not yet created.

## 1. Task overview

The goal of Task 3 was to build a Python tool that monitors the Docker containers used by the local Frappe CRM project. The tool reports container state and health, captures CPU and memory usage for running containers, scans recent logs for likely errors, and writes a health report in JSON. It also provides an optional auto-restart mode for stopped containers.

The tool is intended for a developer's local Compose stack. Monitoring is the default behavior; containers are only started when the operator explicitly supplies `--auto-restart`.

## 2. Architecture

The existing Compose configuration in `docker/docker-compose.yml` defines the `crm` project and its Frappe, Redis, and MariaDB services. The monitor uses the Docker CLI rather than changing the Frappe application or requiring a new Python dependency.

```text
PowerShell / command line
          |
          v
docker_monitor.py: parse options (--project, --output, --auto-restart)
          |
          v
Docker CLI wrapper (subprocess; timeout and error handling)
          |
          +--> docker ps / inspect  --> select project containers and read state
          +--> docker stats        --> one-time CPU and memory snapshot
          +--> docker logs         --> scan the latest 100 log lines
          +--> docker start        --> only when --auto-restart is enabled
          |
          v
Build a report dictionary and calculate overall status
          |
          v
JSON printed to the terminal or written to the requested file

Unit tests --> mock Docker responses --> verify parsing and behavior without
                                      starting or changing real containers
```

### Main code areas

- `run_docker()` runs Docker commands as an argument list, captures output, applies a timeout, and raises a clear error if Docker is unavailable or a command fails.
- `discover_containers()` filters on the Docker Compose project label, then uses `inspect` to get details for matching containers.
- `summarize_container()` extracts the container ID, name, image, state, health, exit code, and Docker-reported error.
- `get_container_stats()` requests a single CPU and memory snapshot for a running container.
- `collect_log_errors()` scans up to the latest 100 log lines and includes a bounded set of matching examples in the report.
- `start_container()` starts a container and inspects it again to obtain refreshed state. `build_report()` calls it only for stopped states when auto-restart is explicitly enabled.
- `build_report()` combines the collected data and marks the overall status `healthy` or `needs_attention`.
- `main()` parses command-line options, serializes the report as JSON, writes it to a file or standard output, and returns a process exit code.

## 3. Implementation and usage

The implementation was added in `docker_monitor.py`. Unit tests were added in `tests/test_docker_monitor.py`.

### Why I used two files

I kept the program and its tests in separate files because they have different responsibilities:

- `docker_monitor.py` is the actual program. I run it to inspect the local CRM containers and produce a JSON report. It contains the Docker command wrapper, container discovery, status and resource collection, log scanning, report generation, and optional restart behavior.
- `tests/test_docker_monitor.py` is the test suite. It supplies sample container data and mocked Docker responses, then checks that the program returns the expected results. Running the tests does not require Docker and does not start or change containers.

The test file imports `docker_monitor` and calls its functions; the monitor does not depend on the test file. If I left out `docker_monitor.py`, there would be no monitoring program to run. If I left out the test file, the program could still run, but I would lose repeatable checks to catch regressions when changing it. Keeping the files separate also prevents test code from being mixed into the program users run.

### Monitor the default `crm` project and print JSON

```powershell
python .\docker_monitor.py
```

### Save JSON to a file

```powershell
python .\docker_monitor.py --output "$env:TEMP\crm-health-report.json"
Get-Content "$env:TEMP\crm-health-report.json"
```

### Select a different Compose project

```powershell
python .\docker_monitor.py --project another-project
```

### Optional local auto-restart

```powershell
python .\docker_monitor.py --auto-restart
```

This option can start stopped containers in the selected project, so it should only be used when the operator has confirmed that the containers belong to their local environment. The default command does not start or stop containers.

## 4. Testing and observed results

### Automated tests

The focused unit-test command was:

```powershell
python -m unittest discover -s tests -p test_docker_monitor.py -v
```

**Result:** all 9 tests passed. They cover container summary extraction, CPU and memory parsing, log filtering, project-specific discovery, report assembly, JSON file output, the start-and-refresh helper, opt-in restart behavior, and the default no-restart behavior. Docker calls are mocked in these tests.

The following checks also passed:

```powershell
python -m py_compile .\docker_monitor.py
python .\docker_monitor.py --help
git diff --cached --check
```

The monitor successfully wrote a JSON report to a temporary file. In the final local snapshot, the report showed three `crm` containers running: Frappe, Redis, and MariaDB. It included CPU and memory values and reported zero matching log errors, with overall status `healthy`.

The Compose file does not configure Docker health checks, so the report showed `health: "not_configured"`. This means a health check was not configured; it does not mean Docker found the containers unhealthy. CPU readings are snapshots and may vary between runs.

## 5. Issues encountered and how they were resolved

### Docker engine was initially unreachable

The first monitor run reported that the `dockerDesktopLinuxEngine` named pipe could not be found. This indicated that the Docker CLI was installed but its Linux engine was not reachable at that moment. After Docker Desktop was available, `docker info` returned server information and the monitor could inspect the project containers.

### Containers were stopped in the first report

The first successful report found three containers, all in the `exited` state, with no live CPU or memory snapshot. After confirming that these were my local development containers, I ran the monitor with `--auto-restart`. It started the three containers; the subsequent report showed all three as running.

### Log scanner initially counted non-error text

The original log matching was too broad: it could match the `error` substring in a URL such as `ErrorPage.js`, count warning lines that mention an error, and misclassify Redis's `bf-error-rate` metric. I added a regression-test sample for these cases, then refined the filter to match whole error-related words, ignore warning lines, and exclude the Redis metric. The log test and the full 9-test suite passed after the change.

### Python indentation and test-placement mistakes

While adding functions and tests incrementally, a `return` statement was temporarily placed outside its function, and test code was once placed outside the test class or duplicated. Python's syntax check and `unittest` error messages identified those placement problems. The code was re-indented, the duplicate test definition was removed, and the tests were rerun until all 9 passed.

### GitHub comparison initially showed no changes

The first feature branch was based on a different local `main` history than the existing GitHub fork. GitHub therefore showed the branch as identical to the fork's `main`. I created a separate worktree from the fork's `main` and cherry-picked the Task 3 commit into a new branch, `task3-hanumanth572-pr`, so the PR branch shares the fork's history. This kept the original worktree and its unrelated local files untouched.

## 6. Scope and safety

- The original Frappe CRM application code and Compose configuration were not changed for this task.
- Monitoring commands are read-only; only the explicit `--auto-restart` option starts stopped project containers.
- Automated tests mock Docker interactions and do not start or modify containers.
- Log matching is a heuristic for likely errors, not a replacement for reviewing full application logs.
- The final report represents one local snapshot; container state and resource usage can change over time.

## 7. Pull-request preparation

The Task 3 changes and this report are prepared on `task3-hanumanth572-pr`, based on the `main` branch of my fork, `hanumanth572/frappe-crm-devops-internship`. The intended pull-request base is `PearlThoughts-Intern-DevOps/frappe-crm-devops-internship:main`. The pull request has not yet been created.
