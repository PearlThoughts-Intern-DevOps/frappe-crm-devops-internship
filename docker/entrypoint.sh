#!/bin/bash
set -eo pipefail

echo "================================================================="
echo "   Frappe CRM Container Starting on AWS ECS Fargate              "
echo "   Strategy: Blue-Green Deployment with Application Load Balancer"
echo "================================================================="

DB_HOST="${DB_HOST:-mariadb}"
DB_PORT="${DB_PORT:-3306}"
DB_NAME="${DB_NAME:-Admin}"
DB_USER="${DB_USER:-Admin}"
DB_PASSWORD="${DB_PASSWORD:-AdminSecure2026!}"
REDIS_CACHE_URL="${REDIS_CACHE_URL:-redis://redis:6379}"
REDIS_QUEUE_URL="${REDIS_QUEUE_URL:-redis://redis:6379}"
REDIS_SOCKETIO_URL="${REDIS_SOCKETIO_URL:-redis://redis:6379}"
SITE_NAME="${SITE_NAME:-crm.localhost}"
ADMIN_PASSWORD="${ADMIN_PASSWORD:-Admin}"
AUTO_MIGRATE="${AUTO_MIGRATE:-1}"

# Non-SSL client config for MariaDB
cat << EOF > /home/frappe/.my.cnf
[client]
ssl=0
host=${DB_HOST}
port=${DB_PORT}
user=${DB_USER}
password="${DB_PASSWORD}"
EOF
chmod 600 /home/frappe/.my.cnf

echo "[INFO] Waiting for database at ${DB_HOST}:${DB_PORT}..."
until mariadb-admin --defaults-file=/home/frappe/.my.cnf ping --silent 2>/dev/null; do
    echo "[INFO] Database not ready yet. Retrying in 3s..."
    sleep 3
done
echo "[SUCCESS] Connected to database at ${DB_HOST}:${DB_PORT}."

cd /home/frappe/frappe-bench

echo "[INFO] Setting database and Redis host configurations..."
bench set-mariadb-host "${DB_HOST}"
bench set-redis-cache-host "${REDIS_CACHE_URL}"
bench set-redis-queue-host "${REDIS_QUEUE_URL}"
bench set-redis-socketio-host "${REDIS_SOCKETIO_URL}"

# Ensure crm is in sites/apps.txt
grep -qxF 'crm' sites/apps.txt 2>/dev/null || echo 'crm' >> sites/apps.txt

# Ensure Python can resolve frappecrm alias to crm
SITE_PKGS=$(./env/bin/python -c "import site; print(site.getsitepackages()[0])" 2>/dev/null || echo "")
if [ -n "${SITE_PKGS}" ] && [ -d "apps/crm/crm" ] && [ ! -e "${SITE_PKGS}/frappecrm" ]; then
    ln -sf /home/frappe/frappe-bench/apps/crm/crm "${SITE_PKGS}/frappecrm" || true
fi

# Clean up any legacy or corrupt app references in database
echo "[INFO] Cleaning up any legacy app references in database..."
mariadb --defaults-file=/home/frappe/.my.cnf -e "DELETE FROM \`${DB_NAME}\`.\`tabInstalled Application\` WHERE name='frappecrm';" 2>/dev/null || true
mariadb --defaults-file=/home/frappe/.my.cnf -e "UPDATE \`${DB_NAME}\`.\`tabDefaultValue\` SET defvalue=REPLACE(defvalue, '\"frappecrm\"', '\"crm\"') WHERE defkey='installed_apps';" 2>/dev/null || true
mariadb --defaults-file=/home/frappe/.my.cnf -e "DELETE FROM \`${DB_NAME}\`.\`tabModule Def\` WHERE name='FCRM';" 2>/dev/null || true

TABLE_COUNT=$(mariadb --defaults-file=/home/frappe/.my.cnf -sse "SELECT COUNT(*) FROM information_schema.TABLES WHERE TABLE_SCHEMA = '${DB_NAME}';" 2>/dev/null || echo "0")
echo "[INFO] Detected ${TABLE_COUNT} tables in database '${DB_NAME}'."

if [ -f "sites/${SITE_NAME}/site_config.json" ]; then
    echo "[INFO] Site '${SITE_NAME}' config exists. Verifying crm app..."
    bench --site "${SITE_NAME}" install-app crm --force || true
    bench --site "${SITE_NAME}" set-config developer_mode 0
    bench --site "${SITE_NAME}" set-config server_script_enabled 1
    bench --site "${SITE_NAME}" execute crm.install.after_install || true
    bench --site "${SITE_NAME}" clear-cache || true
    if [ "${AUTO_MIGRATE}" = "1" ]; then
        bench --site "${SITE_NAME}" migrate || true
    fi
elif [ "${TABLE_COUNT}" -gt 20 ]; then
    echo "[INFO] Existing tables found. Configuring site '${SITE_NAME}'..."
    mkdir -p "sites/${SITE_NAME}/logs" "sites/${SITE_NAME}/public/files" "sites/${SITE_NAME}/locks"
    cat << JSON > "sites/${SITE_NAME}/site_config.json"
{
 "db_name": "${DB_NAME}",
 "db_password": "${DB_PASSWORD}",
 "db_type": "mariadb",
 "db_host": "${DB_HOST}",
 "db_port": ${DB_PORT}
}
JSON
    bench --site "${SITE_NAME}" install-app crm --force || true
    bench --site "${SITE_NAME}" set-config developer_mode 0
    bench --site "${SITE_NAME}" set-config server_script_enabled 1
    bench --site "${SITE_NAME}" execute crm.install.after_install || true
    bench --site "${SITE_NAME}" clear-cache || true
    if [ "${AUTO_MIGRATE}" = "1" ]; then
        bench --site "${SITE_NAME}" migrate || true
    fi
else
    echo "[INFO] Fresh installation required. Initializing site '${SITE_NAME}'..."
    bench new-site "${SITE_NAME}" \
        --force \
        --db-name "${DB_NAME}" \
        --db-password "${DB_PASSWORD}" \
        --mariadb-root-username "${DB_USER}" \
        --mariadb-root-password "${DB_PASSWORD}" \
        --admin-password "${ADMIN_PASSWORD}" \
        --mariadb-user-host-login-scope='%' || true

    echo "[INFO] Installing Frappe CRM app on '${SITE_NAME}'..."
    bench --site "${SITE_NAME}" install-app crm --force
    bench --site "${SITE_NAME}" set-config developer_mode 0
    bench --site "${SITE_NAME}" set-config server_script_enabled 1
    bench --site "${SITE_NAME}" execute crm.install.after_install || true
    bench --site "${SITE_NAME}" clear-cache
fi

echo "${SITE_NAME}" > sites/currentsite.txt
bench use "${SITE_NAME}"

shutdown() {
    echo "[INFO] Caught termination signal. Gracefully stopping..."
    pkill -TERM -P $$ 2>/dev/null || true
    wait
    exit 0
}
trap shutdown SIGTERM SIGINT

echo "================================================================="
echo "[SUCCESS] Starting Frappe CRM application server on port 8000..."
echo "================================================================="

exec bench start
