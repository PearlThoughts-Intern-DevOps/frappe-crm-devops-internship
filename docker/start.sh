#!/usr/bin/env bash
set -Eeuo pipefail

BENCH_DIR="/home/frappe/frappe-bench"
: "${MYSQL_ROOT_PASSWORD:?Set MYSQL_ROOT_PASSWORD in .env}"
: "${FRAPPE_ADMIN_PASSWORD:?Set FRAPPE_ADMIN_PASSWORD in .env}"

mkdir -p "$BENCH_DIR"
chown -R frappe:frappe "$BENCH_DIR"

# This development MariaDB service has no TLS listener.
printf '[client]\nskip-ssl\n' > /home/frappe/.my.cnf
chown frappe:frappe /home/frappe/.my.cnf
chmod 600 /home/frappe/.my.cnf
printf 'export MYSQL_ROOT_PASSWORD=%q\nexport FRAPPE_ADMIN_PASSWORD=%q\n' \
	"$MYSQL_ROOT_PASSWORD" "$FRAPPE_ADMIN_PASSWORD" > /home/frappe/.crm.env
chown frappe:frappe /home/frappe/.crm.env
chmod 600 /home/frappe/.crm.env

export PATH="/home/frappe/.nvm/versions/node/v24.22.2/bin:/home/frappe/.pyenv/shims:/home/frappe/.local/bin:/home/frappe/.pyenv/bin:/usr/local/bin:/usr/bin:/bin"

# Prepare Frappe first so Vite links against the matching framework UI source.
run_frappe_init() {
	local mode="$1"
	su -l -s /bin/bash frappe -c "source /home/frappe/.crm.env && bash -lc '/workspace/init.sh $mode'"
}

run_frappe_init prepare
mkdir -p /frappe
ln -sfn "$BENCH_DIR/apps/frappe/ui" /frappe/ui

cd "$BENCH_DIR/apps/crm/frontend"
yarn install --check-files
yarn build

exec su -l -s /bin/bash frappe -c "source /home/frappe/.crm.env && bash -lc '/workspace/init.sh start'"
