#!/bin/bash
set -e

echo "Waiting for MariaDB..."
until (echo > /dev/tcp/mariadb/3306) 2>/dev/null; do sleep 5; done
echo "Waiting for Redis..."
until (echo > /dev/tcp/redis/6379) 2>/dev/null; do sleep 5; done

cd /home/frappe

echo "Creating Frappe bench..."
bench init --skip-redis-config-generation frappe-bench --version version-15
cd frappe-bench

bench set-mariadb-host mariadb
bench set-redis-cache-host redis://redis:6379
bench set-redis-queue-host redis://redis:6379
bench set-redis-socketio-host redis://redis:6379

sed -i '/redis/d' ./Procfile
sed -i '/watch/d' ./Procfile

bench get-app crm --branch main

echo "Disabling SSL for the mariadb client..."
printf '[client]\nskip-ssl\n' > /home/frappe/.my.cnf

bench new-site crm.localhost \
  --force \
  --mariadb-root-password "$MARIADB_ROOT_PASSWORD" \
  --admin-password "$FRAPPE_ADMIN_PASSWORD" \
  --mariadb-user-host-login-scope='%'

bench --site crm.localhost install-app crm
bench --site crm.localhost set-config developer_mode 1
bench --site crm.localhost clear-cache
bench use crm.localhost

exec bench start