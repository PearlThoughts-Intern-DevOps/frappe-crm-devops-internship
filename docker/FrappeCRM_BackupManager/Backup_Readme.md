# Frappe CRM Backup Automation, Verification & Disaster Recovery System

A production-grade Python CLI package that orchestrates automated database and file backups for Frappe CRM (`bench`), performs two-layer archive and cryptographic verification (streaming SHA-256 + header/trailer inspection), enforces an atomic rolling retention policy (keeping the latest 7 backup sets), and executes isolated disaster recovery restorations with post-restore ORM smoke testing.

---

## 1. System Architecture & Key Guarantees

Native `bench backup --with-files` generates raw artifacts without checksum digests, retention bounds, or restoration safety gates. `backup_manager` wraps Frappe Bench with five operational guarantees:

1. **Atomic Backup Set Grouping (`models.py`)**: Groups all 4 interdependent Frappe artifacts (`database.sql.gz`, `files.tar`, `private-files.tar`, `site_config_backup.json`) plus generated verification metadata (`manifest.json`, `checksums.sha256`) by their shared `YYYYMMDD_HHMMSS` timestamp prefix. Incomplete or orphaned runs never evict valid backups.
2. **Two-Layer Integrity Verification (`verifier.py`)**:
   - **Layer 1 (Structural Inspection)**: Validates the `.sql.gz` magic header (`\x1f\x8b`) and streams through `zlib` to verify the trailing CRC32 and uncompressed byte size; verifies `.tar` member headers via `tarfile`; validates `site_config_backup.json` JSON keys.
   - **Layer 2 (Cryptographic Hashing)**: Streams artifacts in 64 KB binary chunks (`65536` bytes) to compute SHA-256 digests with flat memory overhead, writing both `manifest.json` and GNU `sha256sum -c` compatible `checksums.sha256` files.
3. **Rolling Retention Policy (`retention.py`)**: Retains strictly the newest $N$ complete backup sets (default `7`) and atomically prunes older sets only after a newly created backup passes verification.
4. **Isolated Test-Site Disaster Recovery (`restore.py`)**:
   - Verifies SHA-256 digests before touching the target site.
   - Automatically bootstraps the isolated test site (`crm-test.localhost`) if absent.
   - Disables background job schedulers (`bench --site <test-site> scheduler disable`) immediately after restore to prevent the test environment from polling production email inboxes or firing duplicate webhooks.
   - Synchronizes `encryption_key` from the backup into the test site's `site_config.json` so encrypted fields remain readable.
   - Executes a post-restore Frappe ORM smoke test (`frappe.db.count('User')`) to verify database responsiveness.
5. **Concurrency Safety (`lock.py`)**: Acquires a non-blocking kernel-level POSIX file lock (`fcntl.flock`) at `/tmp/frappe_backup_manager.lock` to prevent overlapping cron jobs.

---

## 2. Directory Structure

```text
frappe-bench/
├── BACKUP_README.md
├── logs/
│   └── backups.log                  # Rotating audit log (5 MB x 5 files)
├── reports/
│   ├── sample_backup_manifest.json
│   └── sample_verification_report.md
└── scripts/
    ├── backup_manager.py            # Top-level executable CLI entrypoint
    └── backup_manager/              # Modular Python package
        ├── __init__.py
        ├── __main__.py
        ├── cli.py
        ├── config.py
        ├── exceptions.py
        ├── lock.py
        ├── logger.py
        ├── models.py
        ├── restore.py
        ├── retention.py
        ├── runner.py
        └── verifier.py
```

---

## 3. Prerequisites & Setup

### Requirements
- **Python**: 3.10+ (uses standard library only; zero external `pip` dependencies required).
- **Environment**: Works natively inside the Frappe Docker container (`crm-frappe-1`), on a production VM with `bench` in `$PATH`, or from the host OS delegating via `docker exec`.

### Environment Variables (Optional)
| Variable | Default | Description |
|---|---|---|
| `FRAPPE_BENCH_PATH` | Auto-detected | Path to `frappe-bench` directory on the local filesystem |
| `FRAPPE_CONTAINER_NAME` | `crm-frappe-1` | Target Docker container when running from the host OS |
| `FRAPPE_DB_ROOT_PASSWORD` | `123` | MariaDB root password used during test-site restoration |
| `FRAPPE_ADMIN_PASSWORD` | `admin` | Administrator password when bootstrapping a new test site |

### Make the CLI Executable
```bash
chmod +x scripts/backup_manager.py
```

---

## 4. CLI Command Reference

You can invoke the tool either via the top-level script (`python3 scripts/backup_manager.py`) or as a Python module (`python3 -m scripts.backup_manager`).

### 4.1 Run Backup, Generate Manifests & Enforce Retention
```bash
python3 scripts/backup_manager.py backup --site crm.localhost --retention 7 --verify
```
**Sample Output:**
```text
18:15:02 | INFO    | Triggering Frappe backup (--with-files) for site 'crm.localhost'...
18:15:05 | INFO    | Located newly created backup set: 20261104_181502
18:15:05 | INFO    | Computed SHA-256 for database     : 4a5e38f9d12c8b0e... (319175 bytes)
18:15:05 | INFO    | Computed SHA-256 for public_files : e3b0c44298fc1c14... (10240 bytes)
18:15:05 | INFO    | Computed SHA-256 for private_files: f2a1b9c804e17d33... (10240 bytes)
18:15:05 | INFO    | Computed SHA-256 for site_config  : a8c2d1e5b79f4012... (164 bytes)
18:15:05 | INFO    | Generated manifest: 20261104_181502-crm_localhost-manifest.json
18:15:05 | INFO    | Running post-backup verification check...
18:15:05 | INFO    | Verified database     : OK (4a5e38f9d12c8b0e...)
18:15:05 | INFO    | Verified public_files : OK (e3b0c44298fc1c14...)
18:15:05 | INFO    | Verified private_files: OK (f2a1b9c804e17d33...)
18:15:05 | INFO    | Verified site_config  : OK (a8c2d1e5b79f4012...)
18:15:05 | INFO    | Retention policy: Keeping 7 newest set(s) (20261029_020001 to 20261104_181502), pruning 1 older set(s).
18:15:05 | INFO    | Pruned backup set 20261028_020001 (6 files removed, 332.85 KiB freed)
18:15:05 | INFO    | Backup workflow completed successfully for set 20261104_181502.
```

### 4.2 List Discovered Backup Sets
```bash
python3 scripts/backup_manager.py list --site crm.localhost
```
**Sample Output:**
```text
INDEX  TIMESTAMP         COMPLETE   VERIFIED   SIZE (KiB)   RETENTION STATUS
----------------------------------------------------------------------------
1      20261104_181502   YES        YES        333.2        KEEP (1/7)
2      20261103_020001   YES        YES        331.8        KEEP (2/7)
...
7      20261029_020001   YES        YES        328.4        KEEP (7/7)
```

### 4.3 Verify a Specific or Latest Backup Set
```bash
# Verify latest backup set
python3 scripts/backup_manager.py verify --site crm.localhost

# Verify a specific timestamp
python3 scripts/backup_manager.py verify --site crm.localhost --timestamp 20261104_181502
```
You can also verify using standard Linux `sha256sum`:
```bash
cd sites/crm.localhost/private/backups/
sha256sum -c 20261104_181502-crm_localhost-checksums.sha256
```

### 4.4 Prune Old Backups (with Dry-Run Support)
```bash
# Preview sets that would be pruned without deleting files
python3 scripts/backup_manager.py prune --site crm.localhost --retention 7 --dry-run

# Execute live prune
python3 scripts/backup_manager.py prune --site crm.localhost --retention 7
```

### 4.5 Restore into an Isolated Test Site
```bash
python3 scripts/backup_manager.py restore \
  --site crm.localhost \
  --test-site crm-test.localhost \
  --db-root-password 123
```

---

## 5. Exit Codes Reference

For CI/CD pipelines and monitoring alerts, the CLI returns deterministic exit codes:

| Exit Code | Exception / Meaning | Recommended Action |
|---|---|---|
| `0` | Success | None |
| `1` | Configuration / General Error | Check CLI arguments and `logs/backups.log` |
| `2` | `LockError` | Another backup/restore instance is currently running |
| `3` | `BenchCommandError` | Check MariaDB service status and `bench` CLI logs |
| `4` | `VerificationError` | Archive corruption or SHA-256 mismatch detected; do not restore |
| `5` | `RestoreError` | Test-site restoration or post-restore ORM smoke test failed |

---

## 6. Automated Scheduling (Cron)

To run automated daily backups at **02:00 AM IST** with full verification and retention pruning:

```bash
crontab -e
```
Add the following entry:
```cron
0 2 * * * FRAPPE_DB_ROOT_PASSWORD="123" /usr/bin/python3 /home/frappe/frappe-bench/scripts/backup_manager.py backup --site crm.localhost --retention 7 --verify >> /home/frappe/frappe-bench/logs/cron_backup.log 2>&1
```

---

## 7. Disaster Recovery Playbook

Follow these steps during an incident or quarterly recovery drill:

1. **Identify Available Healthy Backups**:
   ```bash
   python3 scripts/backup_manager.py list --site crm.localhost
   ```
2. **Verify Cryptographic Integrity of Target Set**:
   ```bash
   python3 scripts/backup_manager.py verify --site crm.localhost --timestamp <TIMESTAMP>
   ```
3. **Execute Isolated Test Restoration**:
   ```bash
   python3 scripts/backup_manager.py restore --site crm.localhost --test-site crm-test.localhost --timestamp <TIMESTAMP>
   ```
4. **Confirm Post-Restore Checklist**:
   - Confirm `Smoke test PASSED` appears in `logs/backups.log`.
   - Confirm background scheduler is disabled on the test site (`bench --site crm-test.localhost scheduler status`).
   - Inspect public and private attachments in `sites/crm-test.localhost/private/files/`.