# Frappe CRM Backup & Restore Tool

A small Python CLI (`backup.py`) that backs up a Frappe CRM site with Bench commands, verifies backups with SHA-256, keeps the latest 7, and restores into a separate test environment. It doesn't modify the CRM code and stores no credentials.

## Requirements
Python 3.9+ (standard library only), Docker, and the CRM running (container `crm-frappe-1`, site `crm.localhost`). Override with the env vars `FRAPPE_CONTAINER` and `FRAPPE_SITE`.

## Commands
```bash
python3 backup.py backup                 # bench backup, copy out, SHA-256, verify, keep latest 7
python3 backup.py verify [backup_id]     # re-check checksums (exit code 1 if anything changed)
python3 backup.py restore --test-container crm-restore-test-frappe-1 [backup_id]
```

## How it works
- **Backup:** runs `bench --site <site> backup --with-files` in the container and copies the files to `backups/<timestamp>/`. The backup is a consistent snapshot, so the CRM is not locked.
- **SHA-256:** each file's checksum is saved in `backups/<timestamp>/SHA256SUMS` (the same format as the `sha256sum` command). `verify` recomputes and compares.
- **Retention:** only the newest 7 backups are kept.
- **Restore:** verifies the backup, refuses to run against the source container, copies it into the test container and runs `bench restore` there.
- **Logging and errors:** log lines go to the screen and `backup.log`. Failures print one clear line and exit non-zero (1 = verification failed, 2 = error).
- **Reports:** written to `reports/`. Examples are in `sample_reports/`.

## Restore test environment
```bash
cd restore-test
export DB_ROOT_PASSWORD='<choose one>'
export ADMIN_PASSWORD='<choose one>'
docker compose up -d               # first build takes ~10-15 minutes
docker compose logs -f frappe      # wait for "web.1 started"
cd ..
export FRAPPE_DB_ROOT_PASSWORD="$DB_ROOT_PASSWORD"
python3 backup.py restore --test-container crm-restore-test-frappe-1
```
Open http://localhost:8001/crm. After a restore, the login is the backed-up site's. Remove the test stack with `docker compose down -v` inside `restore-test/` only.

## Security
`backups/`, `reports/` and `backup.log` are git-ignored. Backups hold real data and `site_config_backup.json` contains database credentials, so never commit them. SHA-256 checks integrity only, and backups are not encrypted. Retention applies to the local `backups/` folder.