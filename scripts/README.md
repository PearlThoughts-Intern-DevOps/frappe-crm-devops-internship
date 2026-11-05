# Frappe CRM — Backup & Restore Automation Tool

An enterprise-grade, dependency-free Python automation tool for **Frappe CRM**. Automates full database and file backups via Frappe Bench, validates data integrity using cryptographic SHA-256 checksums, enforces automated backup retention policies (keeping the latest 7 backups), and enables safe one-click restoration into isolated test environments.

---

## 1. Architectural Overview

```
                      +---------------------------------------+
                      |       frappe_backup_manager.py        |
                      |        (CLI Entry Point)              |
                      +-------------------+-------------------+
                                          |
        +------------------+--------------+---------------+------------------+
        |                  |                              |                  |
        v                  v                              v                  v
+---------------+  +--------------------+  +--------------------+  +------------------+
| BenchExecutor |  | IntegrityVerifier  |  |  RetentionManager  |  | Report Generator |
| (Bench/Docker)|  | (SHA-256 + Gzip)   |  |  (Latest 7 Backups)|  | (JSON + Markdown)|
+---------------+  +--------------------+  +--------------------+  +------------------+
        |                  |                              |                  |
        v                  v                              v                  v
  Frappe Bench      *.checksums.sha256             Prune older than    Audit Reports in
  CLI Subprocess    *.manifest.json                N retention sets    backups/reports/
```

### Key Modules & Responsibilities:
- **`FrappeBackupManager`**: Master orchestrator controlling the lifecycle of backups, verifications, and restorations.
- **`BenchExecutor`**: Execution abstraction layer supporting native bench environments as well as Docker containerized bench environments.
- **`IntegrityVerifier`**: Computes streaming SHA-256 checksums (64 KiB chunks) and executes deep structural integrity tests (Gzip stream validation, Tarball header checks, and JSON parsing).
- **`RetentionManager`**: Discovers, groups, and chronologically sorts backup sets by timestamp (`YYYYMMDD_HHMMSS`), preserving the latest $N$ backups (default: 7) and purging expired sets.
- **`MariaDB Compatibility Handler`**: Detects and transparently mitigates MariaDB 11 client `NOTE_VERBOSITY` directives (`ERROR 1193`) when restoring to MariaDB 10.8 servers without mutating original backup files.

---

## 2. Key Features

- **Zero External Dependencies**: Engineered strictly using Python's standard library (`hashlib`, `argparse`, `logging`, `subprocess`, `gzip`, `tarfile`, `json`, `pathlib`). Runs immediately on any server without virtualenv or `pip install`.
- **Cryptographic SHA-256 Verification**: Generates standard GNU `sha256sum` compliant files (`.sha256`) and rich metadata manifests (`.manifest.json`).
- **Deep Structural Archive Checking**: Validates internal Gzip headers, CRC32 checksums, and TAR member integrity to prevent silent data corruption or partial file writes.
- **Automated Retention Policy**: Keeps the latest 7 backups by default, automatically purging expired backup sets and reporting freed disk space.
- **Safe Test Environment Restoration**: Enforces pre-restoration integrity checks before touching the target database, and automatically clears cache upon completion.
- **Dual-Destination Logging**: ANSI-colorized, human-readable terminal output combined with detailed persistent file logging (`frappe_backup.log`).
- **Comprehensive Audit Reports**: Automatically outputs structured JSON and formatted Markdown reports for every operation.

---

## 3. Directory Layout

```
scripts/
├── frappe_backup_manager.py     # Main Python automation tool
├── test_backup_manager.py       # Automated unit test suite (14 tests)
├── run_backup.sh                # Linux/macOS Bash launcher (auto-detects Docker)
├── run_backup.ps1               # Windows PowerShell launcher
├── README.md                    # Setup and execution guide
└── samples/                     # Verified sample reports and checksums
    ├── backup_report_sample.json
    ├── backup_report_sample.md
    ├── verification_report_sample.json
    ├── restore_report_sample.json
    ├── restore_report_sample.md
    ├── sample_checksums.sha256
    └── sample_manifest.json
```

---

## 4. Setup & Requirements

### Prerequisites:
- **Python**: 3.8 or higher.
- **Frappe Bench**: Version 5.x or higher with Frappe Framework v15/v16.
- **Database**: MariaDB 10.6+ or 10.8+.

No additional packages are required (`pip install` is not needed).

---

## 5. Execution Guide

You can execute the tool directly inside the bench environment, or from your host using Docker or the provided wrapper scripts.

### Option A: Running Inside Docker Container (Default Dev Environment)
```bash
# Full backup with files, SHA-256 checksums, and retention
docker exec crm-frappe-1 python /workspace/scripts/frappe_backup_manager.py backup --site crm.localhost

# Verify latest backup
docker exec crm-frappe-1 python /workspace/scripts/frappe_backup_manager.py verify --site crm.localhost

# Restore latest backup into test site
docker exec crm-frappe-1 python /workspace/scripts/frappe_backup_manager.py restore --source-site crm.localhost --target-site test.localhost

# List all backups in catalog
docker exec crm-frappe-1 python /workspace/scripts/frappe_backup_manager.py list --site crm.localhost

# Enforce retention policy (keep 7)
docker exec crm-frappe-1 python /workspace/scripts/frappe_backup_manager.py prune --site crm.localhost --retention 7
```

### Option B: Running on Native Linux Server (With Bench Installed)
```bash
cd /home/frappe/frappe-bench
python3 /path/to/scripts/frappe_backup_manager.py backup --site crm.localhost
```

### Option C: Using Platform Launchers

**Linux / macOS Bash Wrapper:**
```bash
chmod +x scripts/run_backup.sh
./scripts/run_backup.sh backup --site crm.localhost
./scripts/run_backup.sh verify --site crm.localhost
./scripts/run_backup.sh restore --source-site crm.localhost --target-site test.localhost
```

**Windows PowerShell Launcher:**
```powershell
.\scripts\run_backup.ps1 backup --site crm.localhost
.\scripts\run_backup.ps1 list --site crm.localhost
.\scripts\run_backup.ps1 restore --source-site crm.localhost --target-site test.localhost
```

---

## 6. CLI Command Reference

### 6.1 `backup` — Create Backup with Verification and Retention
```bash
python frappe_backup_manager.py backup [OPTIONS]
```
| Flag | Default | Description |
| :--- | :--- | :--- |
| `--site` | `crm.localhost` | Target Frappe CRM site name. |
| `--no-files` | `False` | Only backup the database dump (exclude public/private files). |
| `--compress` | `False` | Enable extra compression on files. |
| `--retention` | `7` | Number of recent backups to retain. |
| `--reports-dir` | `<backups>/reports` | Custom output folder for audit reports. |
| `--json` | `False` | Output final summary as JSON to stdout. |

**Example:**
```bash
python frappe_backup_manager.py backup --site crm.localhost --retention 7
```

---

### 6.2 `verify` — Cryptographic Checksum & Format Validation
```bash
python frappe_backup_manager.py verify [OPTIONS]
```
| Flag | Default | Description |
| :--- | :--- | :--- |
| `--site` | `crm.localhost` | Target Frappe CRM site name. |
| `--timestamp` | `None` (latest) | Specific backup timestamp (`YYYYMMDD_HHMMSS`) to verify. |
| `--all` | `False` | Validate every backup set currently present in the directory. |
| `--json` | `False` | Output structured verification report as JSON. |

**Example:**
```bash
python frappe_backup_manager.py verify --site crm.localhost
python frappe_backup_manager.py verify --site crm.localhost --all
```

---

### 6.3 `restore` — Safe Test Environment Restoration
```bash
python frappe_backup_manager.py restore [OPTIONS]
```
| Flag | Default | Description |
| :--- | :--- | :--- |
| `--source-site` | `crm.localhost` | Site containing the source backup. |
| `--target-site` | *(Required)* | Test environment site to restore into (e.g. `test.localhost`). |
| `--timestamp` | `None` (latest) | Specific backup timestamp to restore. Defaults to the latest verified backup. |
| `--mariadb-root-password` | `123` | Root password for MariaDB database server. |
| `--no-files` | `False` | Restore database only, skip public/private file archives. |
| `--force` | `False` | Bypass downgrade warnings during restoration. |

**Example:**
```bash
python frappe_backup_manager.py restore --source-site crm.localhost --target-site test.localhost
```

---

### 6.4 `prune` — Standalone Retention Enforcement
```bash
python frappe_backup_manager.py prune [OPTIONS]
```
| Flag | Default | Description |
| :--- | :--- | :--- |
| `--site` | `crm.localhost` | Target site name. |
| `--retention` | `7` | Keep only the $N$ newest backup sets. |
| `--dry-run` | `False` | Simulate pruning without deleting files. |

**Example:**
```bash
# Preview what would be deleted
python frappe_backup_manager.py prune --site crm.localhost --retention 7 --dry-run

# Execute real cleanup
python frappe_backup_manager.py prune --site crm.localhost --retention 7
```

---

### 6.5 `list` — Backup Catalog & Integrity Status
```bash
python frappe_backup_manager.py list --site crm.localhost
```

Displays a clean table of all backup sets:
```
================================================================================
BACKUP CATALOG FOR SITE: crm.localhost
================================================================================
Timestamp         Created At           Size       DB    Files   SHA256   Manifest
--------------------------------------------------------------------------------
20261104_122524   2026-11-04 12:25:24  336.9 KiB  ✓     ✓       ✓        ✓       
20261104_121436   2026-11-04 12:14:36  335.2 KiB  ✓     ✓       ✓        ✓       
================================================================================
```

---

## 7. Production Automation (Cron Scheduling)

To automate backups on a production or staging server, configure a cron job under the `frappe` user:

```bash
# Edit crontab
crontab -e -u frappe
```

Add the following schedule:

```cron
# Daily backup at 02:00 AM with SHA-256 verification and 7-day retention
0 2 * * * /usr/bin/python3 /home/frappe/frappe-bench/scripts/frappe_backup_manager.py backup --site crm.localhost --retention 7 >> /home/frappe/frappe-bench/logs/cron_backup.log 2>&1

# Weekly integrity check on all historical backups (Sunday at 03:00 AM)
0 3 * * 0 /usr/bin/python3 /home/frappe/frappe-bench/scripts/frappe_backup_manager.py verify --site crm.localhost --all >> /home/frappe/frappe-bench/logs/cron_verify.log 2>&1
```

---

## 8. Running Unit Tests

The test suite thoroughly validates SHA-256 calculation, archive integrity, retention sorting, and SQL sanitization.

```bash
# Inside bench container
docker exec -w /workspace/scripts crm-frappe-1 python test_backup_manager.py

# Or natively
python3 scripts/test_backup_manager.py
```

**Output:**
```
Ran 14 tests in 0.111s

OK
```

---

## 9. Loom Demonstration Script

Use the following 4-step script for your 3-5 minute Loom video walkthrough:

### Scene 1: Introduction (30 seconds)
- **Visual**: Show VS Code workspace and directory tree (`scripts/frappe_backup_manager.py`).
- **Talking Point**: "This is the Python-based Backup & Restore Automation Tool for Frappe CRM. It implements automated backups, SHA-256 cryptographic verification, a 7-backup retention policy, and restoration into a separate test environment."

### Scene 2: Backup Execution & SHA-256 Checksum Generation (60 seconds)
- **Command**:
  ```bash
  docker exec crm-frappe-1 python /workspace/scripts/frappe_backup_manager.py backup --site crm.localhost --retention 7
  ```
- **Show on Screen**:
  - Bench backup execution output.
  - Streaming calculation of SHA-256 checksums.
  - Creation of `.checksums.sha256` and `.manifest.json`.
  - Retention evaluation keeping the latest 7 backups.

### Scene 3: Backup Verification (45 seconds)
- **Command**:
  ```bash
  docker exec crm-frappe-1 python /workspace/scripts/frappe_backup_manager.py verify --site crm.localhost
  ```
- **Show on Screen**:
  - Dual-layer validation: SHA-256 hash match + Gzip CRC32 / Tar integrity checks.
  - All artifacts passing with `[PASS]`.

### Scene 4: Restoration to Test Environment (60 seconds)
- **Command**:
  ```bash
  docker exec crm-frappe-1 python /workspace/scripts/frappe_backup_manager.py restore --source-site crm.localhost --target-site test.localhost
  ```
- **Show on Screen**:
  - Pre-restoration integrity validation.
  - MariaDB compatibility stream sanitization.
  - Successful database and file restoration into `test.localhost`.
  - Cache clearing and verification.

---

# Part 2: Frappe CRM Docker Container Monitoring & Auto-Recovery Tool

A production-grade Python automation tool for monitoring Frappe CRM Docker containers, tracking real-time CPU and memory usage, classifying error logs, generating system health reports in JSON/Markdown, and performing automated self-healing recoveries.

## 10. Architectural Overview

```
                          +------------------------------------------+
                          |        frappe_docker_monitor.py          |
                          |          (CLI / Watch Loop)              |
                          +--------------------+---------------------+
                                               |
         +--------------------+----------------+--------------------+--------------------+
         |                    |                                     |                    |
         v                    v                                     v                    v
+------------------+  +-------------------+                 +-------------------+  +-------------------+
|   DockerClient   |  |   HealthEvaluator |                 |  LogAnalyzer      |  | AutoRecoveryMgr   |
| (Subprocess API) |  | (CPU, Mem, Probes)|                 | (Regex Anomaly)   |  | (Self-Healing)    |
+------------------+  +-------------------+                 +-------------------+  +-------------------+
         |                    |                                     |                    |
         v                    v                                     v                    v
  Docker CLI: ps,      Real-time Stats &                     Classify Errors:      Restart Exited/     
  inspect, stats,      App Ping (Port 8000)                  Python, DB, Redis,    Unhealthy Services  
  logs, restart                                              500/502 Web Errors    (Safe Max Retries)  
```

## 11. Tool Capabilities

- **Automated Container Discovery**: Detects all Frappe CRM services (`crm-frappe-1`, `crm-mariadb-1`, `crm-redis-1`) via compose project label `crm`.
- **Live Telemetry Inspection**: Queries CPU%, memory bytes, memory limit, PIDs count, network I/O, and container uptime.
- **Deep Application Health Probes**: Synthetically verifies Frappe Web (`http://127.0.0.1:8000/api/method/frappe.ping`), MariaDB (3306), and Redis (6379).
- **Intelligent Log Anomaly Scanning**: Classifies errors into `PYTHON_EXCEPTION`, `DATABASE_ERROR`, `REDIS_ERROR`, and `WEB_SERVER_ERROR`.
- **Automated Self-Healing Recovery**: Auto-restarts stopped or unhealthy containers with safeguards (`--dry-run`, `--max-retries`, cooldown verification).
- **Dual Reporting**: Generates JSON health audit reports (`.json`) and Markdown dashboards (`.md`).

## 12. Execution Guide

```bash
# 1. Snapshot Health Check
python scripts/frappe_docker_monitor.py
# Or via Windows PowerShell:
.\scripts\run_monitor.ps1

# 2. Output JSON and Markdown Health Reports
python scripts/frappe_docker_monitor.py \
  --output-json scripts/samples/system_health_report_sample.json \
  --output-md scripts/samples/system_health_report_sample.md

# 3. Simulate Auto-Recovery with Dry-Run
python scripts/frappe_docker_monitor.py --auto-restart --dry-run

# 4. Live Auto-Recovery for Stopped Containers
python scripts/frappe_docker_monitor.py --auto-restart

# 5. Continuous Live Monitoring (5-second refresh)
python scripts/frappe_docker_monitor.py --watch --interval 5
```

## 13. Running Unit Tests

```bash
# Run unit tests with Python standard library
$env:PYTHONPATH = "scripts"
python -m unittest scripts/test_docker_monitor.py
```

**Output:**
```text
Ran 21 tests in 0.151s

OK
```


