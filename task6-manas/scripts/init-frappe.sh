
#!/usr/bin/env bash
set -Eeuo pipefail

BENCH_DIR="/workspace/frappe-bench"
SITE_NAME="crm.localhost"
PYTHON="${BENCH_DIR}/env/bin/python"

: "${DB_ROOT_PASSWORD:?MariaDB root password is required}"
: "${ADMIN_PASSWORD:?Frappe administrator password is required}"

export PIP_DEFAULT_TIMEOUT=120
export PIP_RETRIES=10

echo "======================================"
echo " Starting Frappe CRM Initialization"
echo "======================================"

wait_for_port() {
    local host="$1"
    local port="$2"

    echo "Waiting for ${host}:${port}..."

    for i in $(seq 1 60); do
        if (echo > "/dev/tcp/${host}/${port}") 2>/dev/null; then
            echo "${host}:${port} is available."
            return 0
        fi
        sleep 5
    done

    echo "ERROR: ${host}:${port} is unavailable."
    exit 1
}

wait_for_port mariadb 3306
wait_for_port redis 6379

if [ ! -d "${BENCH_DIR}/apps/frappe" ]; then
    echo "Initializing Frappe Bench..."
    bench init \
        --verbose \
        --python /home/frappe/.pyenv/versions/3.10.13/bin/python3.10 \
        --skip-redis-config-generation \
        "${BENCH_DIR}" \
        --version version-15
else
    echo "Existing Frappe Bench found."
fi

cd "${BENCH_DIR}"

echo "Removing optional WhatsApp app registration..."
if [ -f sites/apps.txt ]; then
    sed -i '/^whatsapp$/d' sites/apps.txt
fi

echo "Registering Frappe Python package..."
"${PYTHON}" -m pip install \
    --no-deps \
    --timeout 120 \
    --retries 10 \
    -e "${BENCH_DIR}/apps/frappe"

echo "Installing Frappe dependencies except GeoLite2..."
"${PYTHON}" -m pip install --timeout 120 --retries 10 tomli

"${PYTHON}" - <<'PY'
import re
import subprocess
import sys
import tomli

pyproject = "/workspace/frappe-bench/apps/frappe/pyproject.toml"

with open(pyproject, "rb") as file:
    config = tomli.load(file)

dependencies = config["project"]["dependencies"]

def normalize(name):
    return re.sub(r"[-_.]+", "-", name).lower()

filtered = []

for dependency in dependencies:
    match = re.match(r"\s*([A-Za-z0-9_.-]+)", dependency)
    if not match:
        raise RuntimeError(f"Cannot parse dependency: {dependency}")

    name = normalize(match.group(1))

    if name == "maxminddb-geolite2":
        print(f"Skipping optional dependency: {name}")
        continue

    filtered.append(dependency)

print(f"Installing {len(filtered)} Frappe dependencies...")

subprocess.run(
    [
        sys.executable,
        "-m",
        "pip",
        "install",
        "--timeout",
        "120",
        "--retries",
        "10",
        *filtered
    ],
    check=True
)
PY

echo "Verifying Frappe installation..."
"${PYTHON}" -c "import frappe, click; print('Frappe installation successful')"

bench set-mariadb-host mariadb
bench set-redis-cache-host redis://redis:6379
bench set-redis-queue-host redis://redis:6379
bench set-redis-socketio-host redis://redis:6379

sed -i '/redis/d' Procfile
sed -i '/watch/d' Procfile

if [ ! -d apps/crm ]; then
    echo "Downloading Frappe CRM..."
    bench get-app crm --branch main
else
    echo "Existing Frappe CRM application found."
fi

echo "Registering Frappe CRM Python package..."
"${PYTHON}" -m pip install \
    --no-deps \
    --timeout 120 \
    --retries 10 \
    -e apps/crm

echo "Verifying application imports..."
"${PYTHON}" -c "import frappe, crm; print('Frappe CRM imports successful')"

if [ ! -f "sites/${SITE_NAME}/site_config.json" ]; then
    echo "Creating CRM site..."
    bench new-site "${SITE_NAME}" \
        --force \
        --mariadb-root-password "${DB_ROOT_PASSWORD}" \
        --admin-password "${ADMIN_PASSWORD}" \
        --no-mariadb-socket
else
    echo "CRM site already exists."
fi

if ! bench --site "${SITE_NAME}" list-apps | grep -qx "crm"; then
    echo "Installing Frappe CRM..."
    bench --site "${SITE_NAME}" install-app crm
else
    echo "CRM application is already installed."
fi

bench --site "${SITE_NAME}" set-config developer_mode 1
bench --site "${SITE_NAME}" set-config mute_emails 1
bench --site "${SITE_NAME}" set-config server_script_enabled 1
bench --site "${SITE_NAME}" clear-cache
bench use "${SITE_NAME}"

echo "======================================"
echo " Frappe CRM initialization completed"
echo "======================================"
