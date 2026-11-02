#!/usr/bin/env bash

set -Eeuo pipefail

: "${MYSQL_ROOT_PASSWORD:?Set MYSQL_ROOT_PASSWORD in .env}"
: "${FRAPPE_ADMIN_PASSWORD:?Set FRAPPE_ADMIN_PASSWORD in .env}"

if [[ -f "/workspaces/frappe_codespace/frappe-bench/apps/frappe" ]]
then
    echo "Bench already exists, skipping init"
    exit 0
fi

source /home/frappe/.nvm/nvm.sh
nvm alias default 18
nvm use 18

echo "nvm use 18" >> ~/.bashrc
cd /workspace

bench init \
    --ignore-exist \
    --skip-redis-config-generation \
    frappe-bench

cd frappe-bench

# Use containers instead of localhost
bench set-mariadb-host mariadb
bench set-redis-cache-host redis://redis-cache:6379
bench set-redis-queue-host redis://redis-queue:6379
bench set-redis-socketio-host redis://redis-socketio:6379

# Remove redis from Procfile
sed -i '/redis/d' ./Procfile


bench new-site dev.localhost \
    --mariadb-root-password "$MYSQL_ROOT_PASSWORD" \
    --admin-password "$FRAPPE_ADMIN_PASSWORD" \
    --no-mariadb-socket

bench --site dev.localhost set-config developer_mode 1
bench --site dev.localhost clear-cache
bench use dev.localhost
bench get-app crm
bench --site dev.localhost install-app crm
