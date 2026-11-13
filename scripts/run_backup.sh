#!/usr/bin/env bash
# ==============================================================================
# Frappe CRM Backup & Restore Automation Tool — Bash Wrapper
# ==============================================================================
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PYTHON_SCRIPT="${SCRIPT_DIR}/frappe_backup_manager.py"
CONTAINER_NAME="crm-frappe-1"

# Check if bench is available locally
if command -v bench >/dev/null 2>&1; then
    exec python3 "${PYTHON_SCRIPT}" "$@"
elif docker ps --format '{{.Names}}' | grep -q "^${CONTAINER_NAME}$"; then
    echo "Bench not found locally. Running inside container '${CONTAINER_NAME}'..."
    exec docker exec -i "${CONTAINER_NAME}" python3 "/workspace/scripts/frappe_backup_manager.py" "$@"
else
    echo "ERROR: Neither local 'bench' nor Docker container '${CONTAINER_NAME}' is available." >&2
    exit 1
fi

