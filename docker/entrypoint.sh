#!/bin/bash
set -e
cd /home/frappe/frappe-bench

cat > sites/common_site_config.json <<EOF
{
  "db_host": "127.0.0.1",
  "redis_cache": "redis://127.0.0.1:6379",
  "redis_queue": "redis://127.0.0.1:6379",
  "redis_socketio": "redis://127.0.0.1:6379",
  "serve_default_site": true,
  "socketio_port": 9000
}
EOF


cat > /home/frappe/.my.cnf <<EOF
[client]
ssl=0
[client-mariadb]
skip-ssl
EOF

echo "Waiting for MariaDB..."
until (echo > /dev/tcp/127.0.0.1/3306) 2>/dev/null; do sleep 3; done
sleep 5

if [ ! -d "sites/crm.localhost" ]; then
  bench new-site crm.localhost \
    --mariadb-root-password "${DB_ROOT_PASSWORD}" \
    --admin-password "${ADMIN_PASSWORD}" \
    --install-app crm \
    --set-default
fi

exec bench start