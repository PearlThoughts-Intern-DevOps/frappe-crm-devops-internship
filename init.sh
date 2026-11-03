#!/usr/bin/env bash
set -Eeuo pipefail

BENCH_DIR="/home/frappe/frappe-bench"
SITE="crm.localhost"
MODE="${1:-start}"

if [[ ! -d "$BENCH_DIR/apps/frappe" ]]; then
	bench init --ignore-exist --skip-redis-config-generation "$BENCH_DIR" --frappe-branch version-15
	# The bench image seeds this with its own default app name.
	printf 'frappe\n' > "$BENCH_DIR/sites/apps.txt"
fi

cd "$BENCH_DIR"

# Use the Compose services instead of local Redis or MariaDB processes.
bench set-mariadb-host mariadb
bench set-redis-cache-host redis://redis:6379
bench set-redis-queue-host redis://redis:6379
bench set-redis-socketio-host redis://redis:6379
sed -i '/redis/d' Procfile
sed -i '/watch/d' Procfile

# Install this checkout, rather than fetching a separate copy of CRM.
if [[ -e apps/crm && ! -f apps/crm/pyproject.toml ]]; then
	mv apps/crm "apps/crm-upstream-$(date +%s)"
fi
if [[ ! -e apps/crm ]]; then
	ln -s /workspace apps/crm
fi
grep -qxF crm sites/apps.txt || echo crm >> sites/apps.txt
uv pip install --quiet -e /workspace --python "$BENCH_DIR/env/bin/python"

if [[ "$MODE" == "prepare" ]]; then
	exit 0
fi

create_site() {
	bench new-site "$SITE" \
		--force \
		--mariadb-root-password "$MYSQL_ROOT_PASSWORD" \
		--admin-password "$FRAPPE_ADMIN_PASSWORD" \
		--no-mariadb-socket
}

if [[ ! -f "sites/$SITE/site_config.json" ]] || ! bench --site "$SITE" list-apps >/dev/null 2>&1; then
	create_site
fi

if ! bench --site "$SITE" list-apps 2>/dev/null | grep -qx crm; then
	bench --site "$SITE" install-app crm
fi

bench --site "$SITE" migrate
bench --site "$SITE" set-config developer_mode 1
bench --site "$SITE" set-config mute_emails 1
bench --site "$SITE" set-config server_script_enabled 1
bench --site "$SITE" clear-cache
bench use "$SITE"

exec bench start
