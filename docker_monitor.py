import re
import argparse
import json
import logging
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

DEFAULT_PROJECT = "crm"


class DockerCommandError(RuntimeError):
    """Raised when a Docker command cannot be completed."""


def run_docker(*arguments: str, include_stderr: bool = False) -> str:
    """Run a Docker command and return its output."""
    try:
        result = subprocess.run(
            ["docker", *arguments],
            capture_output=True,
            text=True,
            check=True,
            timeout=30,
        )
    except FileNotFoundError as error:
        raise DockerCommandError("Docker CLI not found. Is Docker installed and running?") from error
    except subprocess.TimeoutExpired as error:
        raise DockerCommandError("Docker command timed out.") from error
    except subprocess.CalledProcessError as error:
        detail = error.stderr.strip() or error.stdout.strip() or str(error)
        raise DockerCommandError(f"Docker command failed: {detail}") from error

    if include_stderr:
        return result.stdout + result.stderr

    return result.stdout


def discover_containers(project: str = DEFAULT_PROJECT) -> list[dict]:
    """Find all containers belonging to the selected Docker Compose project."""
    output = run_docker(
        "ps",
        "--all",
        "--quiet",
        "--filter",
        f"label=com.docker.compose.project={project}",
    )
    container_ids = [line.strip() for line in output.splitlines() if line.strip()]

    if not container_ids:
        return []

    try:
        details = json.loads(run_docker("inspect", *container_ids))
    except json.JSONDecodeError as error:
        raise DockerCommandError("Docker returned invalid container details.") from error

    if not isinstance(details, list) or not all(
        isinstance(container, dict) for container in details
    ):
        raise DockerCommandError("Docker returned container details in an unexpected format.")

    return details


def summarize_container(container: dict) -> dict:
    """Extract useful status and health details from Docker inspection data."""
    state = container.get("State", {})
    health = state.get("Health") or {}
    container_id = container.get("Id") or ""
    container_name = container.get("Name") or ""

    return {
        "id": container_id[:12] or None,
        "name": container_name.lstrip("/"),
        "image": container.get("Config", {}).get("Image", "unknown"),
        "status": state.get("Status", "unknown"),
        "health": health.get("Status", "not_configured"),
        "exit_code": state.get("ExitCode"),
        "error": state.get("Error") or None,
    }


def get_container_stats(container_id: str) -> dict:
    """Get a one-time CPU and memory snapshot for a container."""
    output = run_docker(
        "stats",
        "--no-stream",
        "--format",
        "{{.CPUPerc}}|{{.MemUsage}}|{{.MemPerc}}",
        container_id,
    )
    parts = output.strip().split("|", maxsplit=2)

    if len(parts) != 3:
        raise DockerCommandError(
            f"Docker returned unexpected stats for container {container_id}."
        )

    memory_parts = parts[1].split("/", maxsplit=1)

    try:
        cpu_percent = float(parts[0].strip().removesuffix("%"))
        memory_percent = float(parts[2].strip().removesuffix("%"))
    except ValueError as error:
        raise DockerCommandError(
            f"Docker returned invalid percentage values for container {container_id}."
        ) from error

    return {
        "cpu_percent": cpu_percent,
        "memory_usage": memory_parts[0].strip(),
        "memory_limit": memory_parts[1].strip() if len(memory_parts) == 2 else None,
        "memory_percent": memory_percent,
    }


def collect_log_errors(container_id: str) -> dict:
    """Collect recent logs and find lines that look like errors."""
    output = run_docker(
        "logs",
        "--tail",
        "100",
        container_id,
        include_stderr=True,
    )
    error_pattern = re.compile(
        r"\b(error|exception|fatal|panic|failed)\b",
        re.IGNORECASE,
    )
    warning_pattern = re.compile(r"\bwarning\b", re.IGNORECASE)

    error_lines = [
        line
        for line in output.splitlines()
        if error_pattern.search(line)
        and not warning_pattern.search(line)
        and not re.search(r"\bbf-error-rate\b", line, re.IGNORECASE)
    ]
    return {
        "error_count": len(error_lines),
        "error_samples": error_lines[:20],
    }

def start_container(container_id: str) -> dict:
    """Start one container and fetch its updated details."""
    run_docker("start", container_id)

    try:
        details = json.loads(run_docker("inspect", container_id))
    except json.JSONDecodeError as error:
        raise DockerCommandError(
            f"Docker returned invalid details after starting {container_id}."
        ) from error

    if not isinstance(details, list) or not details or not isinstance(details[0], dict):
        raise DockerCommandError(
            f"Docker returned unexpected details after starting {container_id}."
        )

    return details[0]

def build_report(
    project: str = DEFAULT_PROJECT,
    auto_restart: bool = False,
) -> dict:
    """Collect container details and build a project health report."""
    containers = discover_containers(project)
    report_containers = []

    for container in containers:
        item = summarize_container(container)
        container_id = container.get("Id")
        if (
            auto_restart
            and item["status"] in ("created", "exited", "dead")
            and container_id
        ):
            try:
                container = start_container(container_id)
                item = summarize_container(container)
                logging.info("Started stopped container %s", item["name"])
            except DockerCommandError as error:
                item["restart_error"] = str(error)
                logging.error(
                    "Could not start container %s: %s",
                    item["name"],
                    error,
                )

        if item["status"] == "running" and container_id:
            try:
                item["resources"] = get_container_stats(container_id)
            except DockerCommandError as error:
                item["stats_error"] = str(error)
        else:
            item["resources"] = None

        if container_id:
            try:
                item["logs"] = collect_log_errors(container_id)
            except DockerCommandError as error:
                item["log_error"] = str(error)
        else:
            item["log_error"] = "Docker did not provide a container ID."

        report_containers.append(item)

    has_issues = not report_containers or any(
        item["status"] != "running"
        or item["health"] == "unhealthy"
        or item.get("logs", {}).get("error_count", 0) > 0
        or "stats_error" in item
        or "log_error" in item
        for item in report_containers
    )

    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "project": project,
        "overall_status": "needs_attention" if has_issues else "healthy",
        "summary": {
            "total_containers": len(report_containers),
            "running_containers": sum(
                item["status"] == "running" for item in report_containers
            ),
            "non_running_containers": sum(
                item["status"] != "running" for item in report_containers
            ),
        },
        "containers": report_containers,
    }
def create_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Monitor containers in the Frappe CRM Docker project."
    )
    parser.add_argument(
        "--project",
        default=DEFAULT_PROJECT,
        help="Docker Compose project name to monitor.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        help="Write the JSON report to this file instead of the terminal.",
    )
    parser.add_argument(
        "--auto-restart",
        action="store_true",
        help="Start stopped containers in this Docker compose project.",
    )
    return parser

def main(argv: list[str] | None = None) -> int:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    arguments = create_parser().parse_args(argv)

    try:
        report = build_report(arguments.project, arguments.auto_restart)
        report_json = json.dumps(report, indent=2) + "\n"

        if arguments.output:
            arguments.output.write_text(report_json, encoding="utf-8")
            logging.info("Report written to %s", arguments.output)
        else:
            sys.stdout.write(report_json)

    except (DockerCommandError, OSError) as error:
        logging.error("%s", error)
        return 2

    return 1 if report["overall_status"] == "needs_attention" else 0


if __name__ == "__main__":
    raise SystemExit(main())
