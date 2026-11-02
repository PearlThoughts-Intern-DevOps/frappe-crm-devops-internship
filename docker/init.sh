#!/bin/bash
set -e

cd /home/frappe

cat > ~/.my.cnf <<'EOF'
[client]
skip-ssl
EOF

if [ -d "frappe-bench/sites/crm.localhost" ]; then
    echo "Site already exists, skipping init"
    cd frappe-bench
    exec bench start
fi

echo "Waiting for MariaDB and Redis..."
until (echo > /dev/tcp/mariadb/3306) 2>/dev/null; do sleep 2; done
until (echo > /dev/tcp/redis/6379) 2>/dev/null; do sleep 2; done

echo "Creating new bench..."
bench init --skip-redis-config-generation frappe-bench --version version-15
cd frappe-bench

bench set-mariadb-host mariadb
bench set-redis-cache-host redis://redis:6379
bench set-redis-queue-host redis://redis:6379
bench set-redis-socketio-host redis://redis:6379

sed -i '/redis/d' ./Procfile
sed -i '/watch/d' ./Procfile

bench get-app crm --branch main

bench new-site crm.localhost \
    --force \
    --mariadb-root-password 123 \
    --admin-password admin \
    --mariadb-user-host-login-scope='%'

bench --site crm.localhost install-app crm
bench --site crm.localhost set-config developer_mode 1
bench --site crm.localhost set-config mute_emails 1
bench --site crm.localhost set-config server_script_enabled 1
bench --site crm.localhost clear-cache
bench use crm.localhost

exec bench start