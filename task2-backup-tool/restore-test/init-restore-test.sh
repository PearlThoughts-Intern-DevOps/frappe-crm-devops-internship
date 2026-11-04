#!/bin/bash
# Builds an EMPTY Frappe CRM site ("restore-test.localhost") that backups get restored into.
# Passwords come from environment variables; nothing is hard-coded.
set -e
cd /home/frappe
git config --global http.version HTTP/1.1

cat > ~/.my.cnf <<'EOF'
[client]
skip-ssl
EOF

if [ -d "frappe-bench/sites/restore-test.localhost" ]; then
    echo "Test site already exists, starting"
    cd frappe-bench
    exec bench start
fi

until (echo > /dev/tcp/mariadb/3306) 2>/dev/null; do sleep 2; done
until (echo > /dev/tcp/redis/6379) 2>/dev/null; do sleep 2; done

bench init --skip-redis-config-generation frappe-bench --version version-15
cd frappe-bench

bench set-mariadb-host mariadb
bench set-redis-cache-host redis://redis:6379
bench set-redis-queue-host redis://redis:6379
bench set-redis-socketio-host redis://redis:6379

sed -i '/redis/d' ./Procfile
sed -i '/watch/d' ./Procfile

bench get-app crm --branch main

bench new-site restore-test.localhost \
    --force \
    --mariadb-root-password "$DB_ROOT_PASSWORD" \
    --admin-password "$ADMIN_PASSWORD" \
    --mariadb-user-host-login-scope='%'

bench --site restore-test.localhost install-app crm
bench --site restore-test.localhost set-config mute_emails 1
bench --site restore-test.localhost clear-cache
bench use restore-test.localhost

exec bench start
