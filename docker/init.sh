#!/bin/bash

set -e

# Disable SSL for MariaDB client so it connects to local MariaDB container without TLS errors
cat << 'EOF' > /home/frappe/.my.cnf
[client]
ssl=0

[mysql]
ssl=0

[mariadb]
ssl=0

[mariadb-client]
ssl=0
EOF

if [ ! -d "/home/frappe/frappe-bench/apps/frappe" ]; then
    echo "Creating new bench..."
    bench init --skip-redis-config-generation frappe-bench --version version-15
    cd frappe-bench

    # Use containers instead of localhost
    bench set-mariadb-host mariadb
    bench set-redis-cache-host redis://redis:6379
    bench set-redis-queue-host redis://redis:6379
    bench set-redis-socketio-host redis://redis:6379

    # Remove redis, watch from Procfile
    sed -i '/redis/d' ./Procfile
    sed -i '/watch/d' ./Procfile

    bench get-app crm --branch main
else
    cd frappe-bench
fi

if [ ! -d "/home/frappe/frappe-bench/sites/crm.localhost" ]; then
    echo "Setting up site crm.localhost..."
    bench new-site crm.localhost \
        --force \
        --mariadb-root-password 123 \
        --admin-password admin \
        --no-mariadb-socket

    bench --site crm.localhost install-app crm
    bench --site crm.localhost set-config developer_mode 1
    bench --site crm.localhost set-config mute_emails 1
    bench --site crm.localhost set-config server_script_enabled 1
    bench --site crm.localhost clear-cache
    bench use crm.localhost
fi

echo "Starting bench..."
bench start