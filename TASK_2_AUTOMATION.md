# Task 2: Python Automation for Frappe CRM - Backup & Restore Automation Tool

**Author:** Bulbul Das ([@dasBulbul03](https://github.com/dasBulbul03))  
**Role:** DevOps Engineering Intern  
**Organization:** PearlThoughts  
**Repository:** `PearlThoughts-Intern-DevOps/frappe-crm-devops-internship`  
**Submission Date:** November 2026  

---

## 1. Executive Summary

This report documents the implementation and validation of **Task 2: Python Automation for Frappe CRM**, executed as part of the PearlThoughts DevOps Internship Program.

The core objective was to build an enterprise-ready, Python-based **Backup and Restore Automation Tool** that eliminates manual bench maintenance, provides cryptographic verification, enforces automated storage retention, and enables risk-free restoration testing into an isolated environment without modifying application source code or compromising production data.

---

## 2. Requirements & Implementation Matrix

| Requirement | Implementation Details | Verification Status |
| :--- | :--- | :--- |
| **1. Automated Backups** | Executes `bench --site <site> backup --with-files` via auto-detected Docker or Native backends; captures database SQL gzip, public files tar, private files tar, and site config JSON. | **PASSED & VERIFIED** |
| **2. SHA-256 Verification** | Computes cryptographic SHA-256 hashes in 64 KiB stream chunks for all backup files; writes `checksums.sha256` and `manifest.json`; performs structural gzip/tar integrity checks. | **PASSED & VERIFIED** |
| **3. Retention Policy (7 Backups)** | Tracks backup snapshots chronologically; automatically prunes the oldest snapshots when count exceeds 7; logs all reclaimed disk space. | **PASSED & VERIFIED** |
| **4. Separate Test Environment Restore** | Restores backups strictly into an isolated test site (`test.localhost`); enforces a hard safety block against restoring to production (`crm.localhost`); verifies post-restore table and DocType counts. | **PASSED & VERIFIED** |
| **5. Logging & Error Handling** | Implements multi-channel logging (stdout + `frappe_backup.log`); includes custom exception hierarchy; masks sensitive credentials (`--mariadb-root-password`, `-p`, tokens) with `***`. | **PASSED & VERIFIED** |
| **6. Command-Line Interface (CLI)** | Comprehensive `argparse` CLI supporting subcommands: `backup`, `verify`, `restore`, `list`, `prune` with global configuration flags. | **PASSED & VERIFIED** |

---

## 3. Architecture & Data Flow

```mermaid
sequenceDiagram
    autonumber
    actor DevOps as DevOps Engineer
    participant Tool as Python Automation Tool (backup_manager.py)
    participant Bench as Frappe Bench Container (crm-frappe-1)
    participant Storage as Local Backup Storage (/backups)
    participant TestDB as MariaDB (test.localhost)

    Note over DevOps,Tool: Phase 1: Automated Backup & Checksumming
    DevOps->>Tool: python3 backup_manager.py backup
    Tool->>Bench: bench --site crm.localhost backup --with-files
    Bench-->>Tool: Return database.sql.gz, files.tar, site_config.json
    Tool->>Storage: Store snapshot in /backups/<timestamp>_crm_localhost/
    Tool->>Tool: Compute SHA-256 hashes & write manifest.json
    Tool->>Storage: Enforce 7-backup retention policy (prune oldest)

    Note over DevOps,Tool: Phase 2: Cryptographic Verification
    DevOps->>Tool: python3 backup_manager.py verify
    Tool->>Storage: Read manifest.json & calculate current SHA-256
    Tool->>Tool: Validate GZIP & TAR archive structures
    Tool-->>DevOps: Print Verification Report (Status: VALID)

    Note over DevOps,Tool: Phase 3: Safe Restoration Testing
    DevOps->>Tool: python3 backup_manager.py restore --target-site test.localhost
    Tool->>Tool: Assert target != production (Safety Guard)
    Tool->>Tool: Run pre-restore SHA-256 check
    Tool->>Tool: Sanitize cross-version MariaDB dump
    Tool->>Bench: bench --site test.localhost restore <dump> --with-files
    Bench->>TestDB: Populate test database tables
    Tool->>Bench: bench --site test.localhost mariadb "SELECT count(*) FROM tabDocType;"
    Tool-->>DevOps: Return Success Report (Verified DocTypes: 329)
```

---

## 4. Key DevOps Findings & Solutions

### 4.1 Cross-Version MariaDB Dump Compatibility
* **Issue:** The Frappe Bench image uses MariaDB Dump v11.8, while the containerized database service runs MariaDB 10.8. The dump generator injects `/*M!100616 SET @OLD_NOTE_VERBOSITY=@@NOTE_VERBOSITY, NOTE_VERBOSITY=0 */;`. During restore on MariaDB 10.8, this triggered `ERROR 1193 (HY000): Unknown system variable 'NOTE_VERBOSITY'`, causing native `bench restore` to abort.
* **Resolution:** The automation tool dynamically creates an in-flight sanitized stream of the database dump removing the unsupported directive before triggering restore. This allows smooth restoration without modifying application code or database configuration.

### 4.2 Production Safety Assertion
* **Requirement:** Never overwrite production data during testing.
* **Resolution:** The script enforces an unconditional safety guard:
  ```python
  if target_site == self.source_site:
      raise RestoreSafetyError(
          f"CRITICAL SAFETY VIOLATION: Refusing to restore into production/source site '{self.source_site}'!"
      )
  ```
  Attempting to target `crm.localhost` aborts execution immediately with exit code 1.

### 4.3 Sensitive Credentials Masking
* All logging passes through a custom `SensitiveDataFilter` that scrubs root passwords, database passwords, and auth tokens, replacing them with `***` across both terminal and log files.

---

## 5. Execution Verification

### 5.1 Backup Creation
```bash
$ python3 automation/backup_manager.py backup

[INFO] Auto-detection: Found active container 'crm-frappe-1'. Using Docker mode.
[INFO] Initiating full backup for site: 'crm.localhost'
[INFO] Bench backup completed successfully inside environment.
[INFO]   [DATABASE     ] 20261104_160131-crm_localhost-database.sql.gz (283.29 KiB) | SHA-256: 968333c3384c...
[INFO]   [PUBLIC_FILES ] 20261104_160131-crm_localhost-files.tar (10.00 KiB) | SHA-256: 43aa98b34ce4...
[INFO]   [PRIVATE_FILES] 20261104_160131-crm_localhost-private-files.tar (10.00 KiB) | SHA-256: 17d07fa6b201...
[INFO]   [SITE_CONFIG  ] 20261104_160131-crm_localhost-site_config_backup.json (164.00 B) | SHA-256: 3ea7b0b4060b...
[INFO] Backup manifest saved to: backups/20261104_160131_crm_localhost/manifest.json
[INFO] Evaluating backup retention policy (Limit: latest 7 backups)...
[INFO] Retention policy check: Retained within limit.
```

### 5.2 Backup Verification
```bash
$ python3 automation/backup_manager.py verify

[INFO] Verifying backup in: backups/20261104_160131_crm_localhost
[INFO]   [DATABASE     ] database.sql.gz      | Hash: MATCH | Format: VALID | Status: PASSED
[INFO]   [PUBLIC_FILES ] files.tar            | Hash: MATCH | Format: VALID | Status: PASSED
[INFO]   [PRIVATE_FILES] private-files.tar    | Hash: MATCH | Format: VALID | Status: PASSED
[INFO]   [SITE_CONFIG  ] site_config.json     | Hash: MATCH | Format: VALID | Status: PASSED
[INFO] All checksums and archives for backup '20261104_160131_crm_localhost' verified successfully.
```

### 5.3 Test Environment Restore
```bash
$ python3 automation/backup_manager.py restore --target-site test.localhost

[INFO] Starting safe restoration pipeline -> Target Test Site: 'test.localhost'
[INFO] Performing pre-restoration SHA-256 verification... PASSED
[INFO] Sanitizing SQL dump for cross-version MariaDB compatibility...
[INFO] Executing bench restore into 'test.localhost'...
[INFO] Performing post-restoration verification query...
[INFO] SUCCESS: Site 'test.localhost' successfully restored! Verified DocType count: 329.
[INFO] Production site 'crm.localhost' remains 100% untouched and safe.
```

---

## 6. Deliverables Reference

* **Python Tool:** [`automation/backup_manager.py`](automation/backup_manager.py)
* **Tool Documentation:** [`automation/README.md`](automation/README.md)
* **Sample Reports:**
  * Backup Metadata Report: [`automation/reports/sample_backup_report.json`](automation/reports/sample_backup_report.json)
  * Verification Report: [`automation/reports/sample_verification_report.json`](automation/reports/sample_verification_report.json)
  * Restoration Report: [`automation/reports/sample_restore_report.json`](automation/reports/sample_restore_report.json)
* **Log File:** [`automation/logs/frappe_backup.log`](automation/logs/frappe_backup.log)
