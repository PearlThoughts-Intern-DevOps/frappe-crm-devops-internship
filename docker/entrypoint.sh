#!/bin/bash
set -eo pipefail

# =============================================================================
# Frappe CRM Production Entrypoint for AWS ECS Fargate
# =============================================================================
# Responsibilities:
# 1. Configures database and Redis client connection parameters
# 2. Waits for RDS MariaDB and Redis readiness
# 3. Initializes site if first run, or executes auto-migration on existing site
# 4. Handles SIGTERM/SIGINT signals for graceful task draining during Blue-Green traffic shift
# 5. Starts Frappe CRM application server (web + worker + scheduler)
# =============================================================================

echo "================================================================="
echo "   Frappe CRM Container Starting on AWS ECS Fargate              "
echo "   Strategy: Blue-Green Deployment with Application Load Balancer"
echo "================================================================="

# Environment defaults
DB_HOST="${DB_HOST:-mariadb}"
DB_PORT="${DB_PORT:-3306}"
DB_NAME="${DB_NAME:-frappe_crm}"
DB_USER="${DB_USER:-root}"
DB_PASSWORD="${DB_PASSWORD:-123}"
REDIS_CACHE_URL="${REDIS_CACHE_URL:-redis://redis:6379}"
REDIS_QUEUE_URL="${REDIS_QUEUE_URL:-redis://redis:6379}"
REDIS_SOCKETIO_URL="${REDIS_SOCKETIO_URL:-redis://redis:6379}"
SITE_NAME="${SITE_NAME:-crm.localhost}"
ADMIN_PASSWORD="${ADMIN_PASSWORD:-admin}"
AUTO_MIGRATE="${AUTO_MIGRATE:-1}"

# Ensure proper non-SSL client config for RDS/MariaDB
mkdir -p /home/frappe/.my.cnf.d 2>/dev/null || true
cat << MYCNF > /home/frappe/.my.cnf
[client]
ssl=0
host=${DB_HOST}
port=${DB_PORT}
user=${DB_USER}
password="${DB_PASSWORD}"
MYCNF
chmod 600 /home/frappe/.my.cnf

# Wait for MariaDB / RDS availability
echo "[INFO] Checking database connectivity at ${DB_HOST}:${DB_PORT}..."
MAX_RETRIES=30
RETRY_COUNT=0
until mariadb-admin ping -h "${DB_HOST}" -P "${DB_PORT}" -u "${DB_USER}" -p"${DB_PASSWORD}" --silent 2>/dev/null; do
    RETRY_COUNT=$((RETRY_COUNT + 1))
    if [ ${RETRY_COUNT} -ge ${MAX_RETRIES} ]; then
        echo "[ERROR] Database at ${DB_HOST}:${DB_PORT} unreachable after ${MAX_RETRIES} attempts. Exiting."
        exit 1
    fi
    echo "[INFO] Waiting for database at ${DB_HOST}:${DB_PORT} (Attempt ${RETRY_COUNT}/${MAX_RETRIES})..."
    sleep 3
done
echo "[SUCCESS] Connected to database at ${DB_HOST}:${DB_PORT}."

cd /home/frappe/frappe-bench

# Set container companion service hostnames in common_site_config.json
echo "[INFO] Setting database and Redis host configurations..."
bench set-mariadb-host "${DB_HOST}"
bench set-redis-cache-host "${REDIS_CACHE_URL}"
bench set-redis-queue-host "${REDIS_QUEUE_URL}"
bench set-redis-socketio-host "${REDIS_SOCKETIO_URL}"

# Ensure MariaDB user for site exists with consistent password and host scope
echo "[INFO] Ensuring MariaDB site user '${DB_NAME}' exists with consistent credentials..."
mariadb -h "${DB_HOST}" -P "${DB_PORT}" -u "${DB_USER}" -p"${DB_PASSWORD}" << SQL || true
CREATE USER IF NOT EXISTS '${DB_NAME}'@'%' IDENTIFIED BY '${DB_PASSWORD}';
ALTER USER '${DB_NAME}'@'%' IDENTIFIED BY '${DB_PASSWORD}';
GRANT ALL PRIVILEGES ON \`${DB_NAME}\`.* TO '${DB_NAME}'@'%';
FLUSH PRIVILEGES;
SQL

# Check if database has been populated with Frappe tables
TABLE_COUNT=$(mariadb -h "${DB_HOST}" -u "${DB_USER}" -p"${DB_PASSWORD}" -sse "SELECT COUNT(*) FROM information_schema.TABLES WHERE TABLE_SCHEMA = '${DB_NAME}';" 2>/dev/null || echo "0")
echo "[INFO] Detected ${TABLE_COUNT} tables in database '${DB_NAME}'."

if [ -f "sites/${SITE_NAME}/site_config.json" ]; then
    echo "[INFO] Local site config for '${SITE_NAME}' exists."
    if [ "${AUTO_MIGRATE}" = "1" ]; then
        echo "[INFO] Running database migrations on ${SITE_NAME}..."
        bench --site "${SITE_NAME}" migrate || echo "[WARN] Migration finished with warnings."
    fi
elif [ "${TABLE_COUNT}" -gt 20 ]; then
    echo "[INFO] Populated database '${DB_NAME}' (${TABLE_COUNT} tables) detected on ${DB_HOST}. Configuring local site..."
    mkdir -p "sites/${SITE_NAME}/logs" "sites/${SITE_NAME}/public/files" "sites/${SITE_NAME}/private/files" "sites/${SITE_NAME}/locks"
    touch "sites/${SITE_NAME}/logs/frappe.log" "sites/${SITE_NAME}/logs/database.log"
    cat << JSON > "sites/${SITE_NAME}/site_config.json"
{
 "db_name": "${DB_NAME}",
 "db_password": "${DB_PASSWORD}",
 "db_type": "mariadb",
 "db_host": "${DB_HOST}",
 "db_port": ${DB_PORT}
}
JSON
    if ! grep -q "crm" "sites/${SITE_NAME}/apps.txt" 2>/dev/null; then
        echo "[INFO] Installing Frappe CRM app on '${SITE_NAME}'..."
        bench --site "${SITE_NAME}" install-app crm || echo "[WARN] install-app finished."
        bench --site "${SITE_NAME}" execute crm.install.after_install || true
    fi
    bench --site "${SITE_NAME}" clear-cache || true
    if [ "${AUTO_MIGRATE}" = "1" ]; then
        echo "[INFO] Running database migrations on ${SITE_NAME}..."
        bench --site "${SITE_NAME}" migrate || true
    fi
else
    echo "[INFO] Fresh installation required: table count is ${TABLE_COUNT}. Initializing new site '${SITE_NAME}'..."
    bench new-site "${SITE_NAME}" \
        --force \
        --db-name "${DB_NAME}" \
        --db-password "${DB_PASSWORD}" \
        --mariadb-root-username "${DB_USER}" \
        --mariadb-root-password "${DB_PASSWORD}" \
        --admin-password "${ADMIN_PASSWORD}" \
        --mariadb-user-host-login-scope='%' || {
            echo "[WARN] new-site command exited non-zero, checking if database exists..."
        }

    echo "[INFO] Installing Frappe CRM app on '${SITE_NAME}'..."
    bench --site "${SITE_NAME}" install-app crm || echo "[WARN] crm app already installed."

    echo "[INFO] Applying production configurations..."
    bench --site "${SITE_NAME}" set-config developer_mode 0
    bench --site "${SITE_NAME}" set-config mute_emails 0
    bench --site "${SITE_NAME}" set-config server_script_enabled 1
    
    echo "[INFO] Executing CRM post-install hooks..."
    bench --site "${SITE_NAME}" execute crm.install.after_install || true

    echo "[INFO] Clearing cache..."
    bench --site "${SITE_NAME}" clear-cache
fi

# Ensure required site subdirectories and log files exist
mkdir -p "sites/${SITE_NAME}/logs" "sites/${SITE_NAME}/public/files" "sites/${SITE_NAME}/private/files" "sites/${SITE_NAME}/locks"
touch "sites/${SITE_NAME}/logs/frappe.log" "sites/${SITE_NAME}/logs/database.log"

# Set active site for web and worker processes
echo "${SITE_NAME}" > sites/currentsite.txt
bench use "${SITE_NAME}"

# Clean Procfile if needed (ensure Redis is not spawned locally)
sed -i '/redis/d' ./Procfile 2>/dev/null || true
sed -i '/watch/d' ./Procfile 2>/dev/null || true

# Configure Administrator credentials and allow login with 'admin' username
if [ -n "${ADMIN_PASSWORD}" ]; then
    echo "[INFO] Configuring Administrator credentials and username alias..."
    bench --site "${SITE_NAME}" set-admin-password "${ADMIN_PASSWORD}" || true
    /home/frappe/frappe-bench/env/bin/python -c "
import frappe
try:
    frappe.init('${SITE_NAME}')
    frappe.connect()
    frappe.db.set_single_value('System Settings', 'allow_login_using_user_name', 1)
    frappe.db.set_value('User', 'Administrator', 'username', 'admin')
    frappe.db.commit()
    print('[SUCCESS] Enabled login with username: admin')
except Exception as e:
    print('[WARN] Could not update admin username:', e)
" || true
fi

# Signal handler for graceful termination on ECS task stop / traffic drain
shutdown() {
    echo "[INFO] Caught SIGTERM/SIGINT signal. Initiating graceful shutdown of Frappe CRM..."
    pkill -TERM -P $$ 2>/dev/null || true
    wait
    echo "[INFO] Frappe CRM terminated cleanly."
    exit 0
}
trap shutdown SIGTERM SIGINT

# Allow running custom command override if arguments provided
if [ $# -gt 0 ]; then
    exec "$@"
fi

echo "================================================================="
echo "[SUCCESS] Frappe CRM initialized successfully. Starting server..."
echo "================================================================="

exec bench start
