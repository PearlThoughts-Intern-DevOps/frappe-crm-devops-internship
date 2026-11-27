#!/bin/bash
set -e

# Disable SSL on MariaDB client to prevent ERROR 2026 TLS/SSL errors
cat << 'EOF' > /home/frappe/.my.cnf
[client]
skip-ssl = true
ssl = 0
EOF

# If bench already exists, start it immediately
if [ -d "/home/frappe/frappe-bench/apps/frappe" ]; then
    echo "Bench already exists! Starting Frappe CRM server..."
    cd /home/frappe/frappe-bench
    bench set-config -g default_site crm.localhost || true
    bench use crm.localhost || true
    echo "crm.localhost" > /home/frappe/frappe-bench/sites/currentsite.txt || true
    exec bench start
fi

echo "Creating new bench..."
cd /home/frappe

bench init --skip-redis-config-generation frappe-bench --version version-15

cd frappe-bench

cat << 'EOF' > .my.cnf
[client]
skip-ssl = true
ssl = 0
EOF

# Point bench to container services
bench set-mariadb-host mariadb
bench set-redis-cache-host redis://redis:6379
bench set-redis-queue-host redis://redis:6379
bench set-redis-socketio-host redis://redis:6379

# Remove redis and watch from Procfile (handled by containers)
sed -i '/redis/d' ./Procfile
sed -i '/watch/d' ./Procfile

echo "Fetching CRM app..."
bench get-app crm --branch main

echo "Waiting for MariaDB connection..."
for i in {1..30}; do
    if (echo > /dev/tcp/mariadb/3306) 2>/dev/null; then
        echo "MariaDB is online!"
        break
    fi
    sleep 2
done

echo "Creating new Frappe CRM site..."
bench new-site crm.localhost \
    --force \
    --mariadb-root-password ${MYSQL_ROOT_PASSWORD:-123} \
    --admin-password ${ADMIN_PASSWORD:-admin} \
    --mariadb-user-host-login-scope='%'

bench --site crm.localhost install-app crm
bench --site crm.localhost set-config developer_mode 1
bench --site crm.localhost set-config mute_emails 1
bench --site crm.localhost set-config server_script_enabled 1
bench --site crm.localhost clear-cache

# Route all incoming requests (including direct IP) to crm.localhost
bench set-config -g default_site crm.localhost
bench use crm.localhost
echo "crm.localhost" > /home/frappe/frappe-bench/sites/currentsite.txt

echo "Frappe CRM setup completed successfully! Starting server..."
exec bench start
