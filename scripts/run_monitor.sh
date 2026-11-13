#!/usr/bin/env bash
# ==============================================================================
# Frappe CRM Docker Monitoring & Auto-Recovery Tool — Bash Wrapper
# ==============================================================================
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PYTHON_SCRIPT="${SCRIPT_DIR}/frappe_docker_monitor.py"
DOCKER_SCRIPT="$(dirname "${SCRIPT_DIR}")/docker/scripts/frappe_docker_monitor.py"

# Sync to docker/scripts if directory exists
if [ -d "$(dirname "${DOCKER_SCRIPT}")" ]; then
    cp -f "${PYTHON_SCRIPT}" "${DOCKER_SCRIPT}" 2>/dev/null || true
fi

# Detect Python 3 runtime
PYTHON_BIN=""
if command -v python3 >/dev/null 2>&1; then
    PYTHON_BIN="python3"
elif command -v python >/dev/null 2>&1; then
    PYTHON_BIN="python"
else
    echo "ERROR: Python 3 runtime not found. Please install Python 3.10+." >&2
    exit 2
fi

export PYTHONPATH="${SCRIPT_DIR}:${PYTHONPATH:-}"

# Execute script with all arguments
exec "${PYTHON_BIN}" "${PYTHON_SCRIPT}" "$@"

