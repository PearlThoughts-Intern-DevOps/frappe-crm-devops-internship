# Frappe CRM Python Backup & Restore Automation Tool

A production-minded, SRE-grade automation tool for Frappe CRM backups, cryptographic verification, automated retention, and isolated disaster recovery restore testing.

---

## 1. Architecture Overview

Frappe CRM runs on the Frappe Framework (v15) inside Docker containers. This automation tool interacts with Frappe Bench CLI using safe, parameterized subprocess execution (no shell string concatenation) and provides end-to-end backup lifecycle management.

```
+-------------------------------------------------------------+
| ORIGINAL CRM PRODUCTION / DEV ENVIRONMENT (PROJECT: crm)    |
| Containers: crm-frappe-1, crm-mariadb-1, crm-redis-1       |
| Host Ports: 8000 (HTTP), 9000 (SocketIO)                    |
| Site: crm.localhost                                         |
| Volume: crm_mariadb-data (STRICTLY PROTECTED / READ-ONLY)   |
+-------------------------------------------------------------+
                            |
                     (Backup Engine)
                            v
+-------------------------------------------------------------+
| HOST BACKUP STORE (OUTSIDE GIT REPOSITORY)                  |
| Path: C:\frappe_crm_backups (or ~/.frappe_backups)          |
| Manifest: manifest.json (SHA-256 Checksums, File Metadata)  |
| Retention Policy: Preserves Latest 7 Verified Backups       |
+-------------------------------------------------------------+
                            |
                     (Restoration Path)
                            v
+-------------------------------------------------------------+
| ISOLATED RESTORE ENVIRONMENT (PROJECT: crm-restore-test)    |
| Containers: crm-restore-test-frappe-1, mariadb, redis       |
| Host Ports: 8005 (HTTP), 9005 (SocketIO)                    |
| Target Site: restore-test.localhost                         |
| Volume: crm-restore-test_mariadb-restore-test-data          |
| Guard: Strictly rejects crm.localhost (Exit Code 4)         |
+-------------------------------------------------------------+
```

---

## 2. Prerequisites & Requirements

- **Python:** Python 3.10+ (Core script uses standard library only: `argparse`, `hashlib`, `json`, `logging`, `pathlib`, `subprocess`).
- **Docker:** Docker Desktop with Docker Compose v2+.
- **Host Storage:** Minimum 1 GB available disk space for backup archives and database dumps.
- **Network Ports:**
  - Original site: `8000`, `9000`
  - Isolated test site: `8005`, `9005` (zero port conflict)

---

## 3. Installation & Setup

1. Clone or navigate to the repository:
   ```bash
   cd frappe-crm-devops-internship
   ```

2. (Optional) Set up a dedicated virtual environment for development and testing:
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # On Windows: .venv\Scripts\Activate.ps1
   pip install -r backup_tool/requirements.txt
   ```

3. Configure environment settings:
   Copy [`backup_tool/config.example.json`](config.example.json) to `backup_tool/config.json` if custom paths are desired:
   ```bash
   cp backup_tool/config.example.json backup_tool/config.json
   ```

---

## 4. Command-Line Interface (CLI) Usage

The tool is invoked via `backup_tool/backup_manager.py`:

```bash
python backup_tool/backup_manager.py [OPTIONS] {backup,verify,list,retention,restore} [ARGS]
```

### Global Options
- `--config FILE`: Path to optional JSON configuration file.
- `--backup-dir DIR`: Directory for backup storage (default: `C:\frappe_crm_backups` or `~/frappe_crm_backups`).
- `--log-file FILE`: Path to write execution log (outside git repository).
- `-v, --verbose`: Enable debug logging.

---

### Command 1: Create Backup (`backup`)

Triggers a full database dump, public files archive, and private files archive using `bench backup --with-files --compress`. Extracts artifacts to host storage, verifies completeness, and writes a cryptographically secured `manifest.json`.

```bash
python backup_tool/backup_manager.py backup
```

**Options:**
- `--site`: Source site to backup (default: `crm.localhost`).
- `--container`: Frappe Docker container name (default: `crm-frappe-1`).
- `--no-compress`: Disable gzip compression (generates uncompressed SQL and TAR files).

---

### Command 2: Cryptographic Verification (`verify`)

Recalculates SHA-256 digests for every backup artifact and verifies them against `manifest.json`. Detects tampered, corrupted, or missing files.

```bash
python backup_tool/backup_manager.py verify --backup-id backup_20261104_080031
```

**Exit Codes:**
- `0`: All checksums match (PASS).
- `3`: Missing file, size discrepancy, or hash mismatch (FAIL).

---

### Command 3: List Backups (`list`)

Displays all discovered backups, timestamps, source sites, and verification statuses in JSON format:

```bash
python backup_tool/backup_manager.py list
```

---

### Command 4: Enforce Retention Policy (`retention`)

Evaluates the backup store, verifies checksums of candidate backups, and preserves the latest `N` (default: 7) verified backups. Older verified backups are safely pruned. Incomplete or unverified backups are never silently deleted.

```bash
python backup_tool/backup_manager.py retention --keep 7
```

---

### Command 5: Isolated Disaster Recovery Restore (`restore`)

Restores a verified backup into an **isolated test environment**.

```bash
python backup_tool/backup_manager.py restore \
  --backup-id backup_20261104_080031 \
  --target-site restore-test.localhost \
  --target-container crm-restore-test-frappe-1 \
  --target-compose-file docker/docker-compose.restore-test.yml
```

> [!CAUTION]
> **Strict Security Guardrails:**
> - Attempting to restore to `crm.localhost` is blocked immediately with **Exit Code 4**.
> - Attempting to target the production/source container `crm-frappe-1` is blocked with **Exit Code 4**.
> - Restoration will not commence if pre-restore SHA-256 verification fails (**Exit Code 3**).

---

## 5. Exit Code Reference

| Exit Code | Classification | Meaning |
| :---: | :--- | :--- |
| **`0`** | `SUCCESS` | Operation completed and validated successfully. |
| **`1`** | `GENERAL_FAILURE` | Command execution error, container down, or unexpected exception. |
| **`2`** | `INVALID_ARGS` | Missing required parameters or invalid configuration. |
| **`3`** | `VERIFICATION_FAILURE` | Checksum mismatch, missing artifact, or corrupted archive. |
| **`4`** | `UNSAFE_RESTORE` | Prohibited destination (`crm.localhost` or primary container targeted). |

---

## 6. Isolated Restore Environment Setup

To run an isolated test environment without impacting the live CRM:

1. Launch the isolated restore test stack:
   ```bash
   docker compose -f docker/docker-compose.restore-test.yml up -d
   ```
2. The isolated stack uses:
   - Compose Project: `crm-restore-test`
   - Ports: `8005:8000` (Web), `9005:9000` (SocketIO)
   - Volume: `crm-restore-test_mariadb-restore-test-data`
   - Test Site: `restore-test.localhost`
3. Execute restore using `backup_manager.py restore`.
4. Verify the restored data by visiting `http://localhost:8005` in your browser.
5. The original site at `http://localhost:8000` remains 100% untouched.

---

## 7. Automated Testing

Run the comprehensive unit test suite:

```bash
python -m unittest discover -s backup_tool/tests -p "test_*.py" -v
```

All subprocess calls in unit tests are mocked to prevent accidental execution against live containers.

---

## 8. Security & Secret Management

- **Credentials:** MariaDB passwords and encryption keys are passed via environment variables (`MARIADB_ROOT_PASSWORD`) or CLI options and are masked (`******`) in all log outputs.
- **Site Configuration:** `site_config_backup.json` is treated as sensitive material containing security keys and is never committed to Git.
- **Git Exclusions:** `.gitignore` excludes all backup directories, database dumps (`*.sql.gz`), archives (`*.tar.gz`), and log files (`*.log`).

