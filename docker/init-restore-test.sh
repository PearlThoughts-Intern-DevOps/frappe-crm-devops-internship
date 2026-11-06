#!/bin/bash
set -e

# Ensure MySQL client does not enforce SSL
echo -e "[client]\nssl=0" > /home/frappe/.my.cnf

if [ ! -d "/home/frappe/frappe-bench/apps/frappe" ]; then
    echo "Waiting for frappe-bench to be populated..."
    sleep 2
fi

if [ -d "/home/frappe/frappe-bench" ]; then
    cd /home/frappe/frappe-bench

    bench set-mariadb-host mariadb
    bench set-redis-cache-host redis://redis:6379
    bench set-redis-queue-host redis://redis:6379
    bench set-redis-socketio-host redis://redis:6379

    sed -i '/redis/d' ./Procfile 2>/dev/null || true
    sed -i '/watch/d' ./Procfile 2>/dev/null || true

    # Ensure crm app exists
    if [ ! -d "apps/crm" ]; then
        bench get-app crm --branch main || true
    fi

    # Create isolated restore-test site if it does not exist
    if [ ! -d "sites/restore-test.localhost" ]; then
        echo "Creating isolated test site: restore-test.localhost..."
        # Remove any stray crm.localhost
        rm -rf sites/crm.localhost 2>/dev/null || true
        bench new-site restore-test.localhost \
            --force \
            --mariadb-root-password 123 \
            --admin-password admin \
            --no-mariadb-socket
        bench --site restore-test.localhost install-app crm
        bench --site restore-test.localhost set-config developer_mode 1
        bench --site restore-test.localhost set-config mute_emails 1
        bench --site restore-test.localhost clear-cache
    fi

    bench use restore-test.localhost
    bench start
else
    echo "frappe-bench directory missing, keeping container alive for provisioning"
    sleep infinity
fi
