# Frappe CRM Backup & Restore Tool

A Python CLI that automates backups of a Frappe CRM site using Frappe Bench commands, verifies them with SHA-256, keeps the latest 7, and restores into a **separate** test environment.

It does not modify the Frappe CRM application code, and it never stores credentials.

## Features

| Requirement | How it is done |
|---|---|
| Database + file backups | Runs `bench --site <site> backup --with-files` (inside the Docker container by default) and copies the files out to `./backups/<id>/` |
| SHA-256 verification | Checksums every file, stores them in `manifest.json`, re-checks after copy and on demand. Also tests that `.sql.gz` / `.tar` archives are readable |
| Retention (latest 7) | After each backup, older backups beyond `--keep` (default 7) are deleted. Only folders that have a `manifest.json` are ever deleted |
| Restore in a test environment | `restore` copies a verified backup into a second, isolated stack and runs `bench restore` there. It refuses to run against the source container |
| Logging + error handling | Console + rotating log file (`logs/backup_tool.log`), clear errors, non-zero exit codes, no partial backups left behind on failure |
| CLI | `backup`, `verify`, `prune`, `list`, `restore` |

Exit codes: `0` success, `1` verification failed, `2` error.

## Requirements

- Python 3.9+ (standard library only, no `pip install` needed)
- Docker (the tool uses `docker exec` / `docker cp`)
- The Frappe CRM stack from Task 1 running (container `crm-frappe-1`)

## Setup

```bash
cd task2-backup-tool
cp .env.example .env        # fill in your own values; .env is git-ignored
```

Check your container name with `docker ps` (default assumed: `crm-frappe-1`, site `crm.localhost`). Override with `--container` and `--site` if different.

## Usage

```bash
# 1. Backup (creates, copies, verifies, writes reports, applies retention)
python3 frappe_backup.py backup

# Database only
python3 frappe_backup.py backup --db-only

# 2. List backups
python3 frappe_backup.py list

# 3. Verify the latest (or a specific id, or all)
python3 frappe_backup.py verify
python3 frappe_backup.py verify 20261104_101500
python3 frappe_backup.py verify --all

# 4. Retention only (preview first)
python3 frappe_backup.py prune --dry-run
python3 frappe_backup.py prune

# 5. Restore into the separate test environment (see below)
export FRAPPE_DB_ROOT_PASSWORD='<test db root password>'
python3 frappe_backup.py restore --test-container crm-restore-test-frappe-1
```

Global options (before the command): `--site`, `--container`, `--local` (run bench on the host, no Docker), `--bench-path`, `--backup-dir`, `--reports-dir`, `--log-file`, `--keep`, `-v`. Run `python3 frappe_backup.py -h` for all of them.

## Restore testing (separate environment)

The restore test environment is its own Docker Compose project (`crm-restore-test`) with its own MariaDB, Redis, bench and volume, on ports 8001/9001. The main stack is never touched.

```bash
cd restore-test
export DB_ROOT_PASSWORD='<choose one>'
export ADMIN_PASSWORD='<choose one>'
docker compose up -d        # first run takes several minutes (builds an empty CRM site)
docker compose logs -f frappe   # wait until bench start is running
cd ..

export FRAPPE_DB_ROOT_PASSWORD="$DB_ROOT_PASSWORD"
python3 frappe_backup.py restore --test-container crm-restore-test-frappe-1
```

Then open `http://localhost:8001/crm` and check the restored data. A restore report is written to `reports/`.

What `restore` does: verifies the backup checksums (refuses if corrupt) → copies files into a staging folder in the test container → `bench --site restore-test.localhost --force restore ...` → clears cache → counts CRM Leads/Deals → removes the staging folder → writes a report.

Tear the test environment down any time with `docker compose down -v` inside `restore-test/`.

## Folder layout

```
frappe_backup.py            the tool
restore-test/               separate test stack (compose + init script)
tests/                      unit tests + mock bench
sample_reports/             example backup and verification reports
backups/  logs/  reports/   created at runtime (backups/ and logs/ are git-ignored)
```

## Tests

```bash
python3 -m unittest discover -s tests -v
```

Eight tests cover checksum creation, corruption detection, missing files, retention (keeps latest 7), dry-run, the restore safety checks, and cleanup after a failed backup. They use a mock `bench` script, so Docker is not needed.

## Sample reports

`sample_reports/` contains an example backup report and verification report. **They were generated against the mock bench used by the tests**, to show the format, so the file contents are tiny. Run `python3 frappe_backup.py backup` against your real stack to produce real ones.

## Security

- No passwords are stored in the repo, logs or reports. The test DB root password is read from `FRAPPE_DB_ROOT_PASSWORD` and passed to the container through the environment, never on the command line.
- `.env`, `backups/` and `logs/` are in `.gitignore`. Backups contain real database content, so never commit them.
- Note: a backup also contains `site_config_backup.json`, which holds the site's database credentials. Keep the `backups/` folder private.

## Notes and limits

- Retention applies to the local `backups/` folder. Copies left inside the container (`sites/<site>/private/backups`) are not deleted by this tool.
- The `restore` command uses `bench restore --db-root-password`. If your bench version names that option differently, check `bench --site <site> restore --help` inside the container.
- Scheduling is not included. To run it daily, use cron, for example: `0 2 * * * cd /path/to/task2-backup-tool && python3 frappe_backup.py backup`.
