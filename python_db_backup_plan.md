# Frappe CRM Backup Automation: 5-Phase Step-by-Step Implementation Plan

## Goal Description
Build an enterprise-grade, automated backup management and disaster recovery CLI tool in Python (`scripts/backup_manager.py`) for Frappe CRM. 

The tool will:
1. Automate database and file backups using Frappe Bench commands.
2. Prevent concurrency conflicts using POSIX process locks (`fcntl`).
3. Model multi-artifact backup snapshots atomically using strict regex grouping.
4. Implement two-stage integrity verification (Structural gzip/tar stream inspection + 64 KB streaming SHA-256).
5. Generate dual manifests (structured JSON and standard Linux `.sha256` files).
6. Enforce a rolling retention policy keeping the latest 7 complete backups (with a fault-tolerant partial-backup guard).
7. Safely restore backups into an isolated test site (`crm-test.localhost`), neutralizing background schedulers, splicing cryptographic encryption keys, and executing an ORM smoke test.
8. Deliver full documentation, sample reports, and a Loom video walkthrough.

---

## The 5-Phase Master Architecture

```
┌────────────────────────────────────────────────────────────────────────┐
│                        Phase 1: Foundation & Runner                    │
│   • POSIX Process Lock (fcntl)      • BackupConfig Dataclass           │
│   • Dual Logging (Console + File)   • BenchRunner (Host/Container)     │
└───────────────────────────────────┬────────────────────────────────────┘
                                    │
                                    ▼
┌────────────────────────────────────────────────────────────────────────┐
│                     Phase 2: Atomic Backup Set Discovery               │
│   • Regex Timestamp Grouping        • BackupSet Dataclass              │
│   • is_complete Validation Guard    • Chronological Sorting            │
└───────────────────────────────────┬────────────────────────────────────┘
                                    │
                                    ▼
┌────────────────────────────────────────────────────────────────────────┐
│                   Phase 3: Deep Verification & Manifests               │
│   • Stage A: Structural Integrity   • Stage B: 64KB Streaming SHA-256  │
│     (gzip CRC32 trailer, tar header)• Dual Manifest (JSON + .sha256)   │
└───────────────────────────────────┬────────────────────────────────────┘
                                    │
                                    ▼
┌────────────────────────────────────────────────────────────────────────┐
│                   Phase 4: Fault-Tolerant Retention Policy             │
│   • Filter only complete sets       • Keep latest 7 snapshots          │
│   • Atomic multi-file unlink        • --dry-run safety simulation      │
└───────────────────────────────────┬────────────────────────────────────┘
                                    │
                                    ▼
┌────────────────────────────────────────────────────────────────────────┐
│                   Phase 5: Disaster Recovery & Safe Restore            │
│   • Pre-flight SHA-256 Gate         • Site Auto-Bootstrap (if missing) │
│   • bench restore invocation        • Schedulers Disabled (Safety)     │
│   • Selective encryption_key Merge  • ORM Smoke Test (db.count User)   │
└────────────────────────────────────────────────────────────────────────┘
```

---

## Phase 1: Foundation, Process Locking & Dual-Context Execution Runner

### 1. Intuition & Rationale
* **The Cron Collision Problem**: In production, backups run on automated crontabs (e.g., nightly at 02:00). If a backup operation takes longer than usual (large database, slow disk I/O, or a database table lock), the next scheduled cron job might start simultaneously. Two scripts running concurrently will fight over disk I/O, compute duplicate checksums, or worse: one script might prune files that the other is currently reading.
  * **Solution**: Non-blocking POSIX advisory locking via `fcntl.flock(lock_file, fcntl.LOCK_EX | fcntl.LOCK_NB)`. If another instance is running, the new instance exits immediately without corrupting data.
* **The Host vs. Container Reality**:
  * On a native Ubuntu server, `bench` lives in `$PATH`.
  * In local development (like your setup), Frappe runs inside Docker container `crm-frappe-1` at `/home/frappe/frappe-bench`, while code editing happens on the host.
  * **Solution**: Auto-detect environment using `shutil.which("bench")`. If `bench` is found, run natively. If not, auto-route commands through `docker exec -w /home/frappe/frappe-bench crm-frappe-1 bench`.

### 2. Code Structure Blueprint (Phase 1)
```python
import os
import sys
import fcntl
import shutil
import logging
import subprocess
from pathlib import Path
from dataclasses import dataclass
from typing import Optional

# Custom Exceptions for clear error tracing
class BackupManagerError(Exception): """Base exception for all tool failures."""
class LockAcquisitionError(BackupManagerError): """Raised when another backup process is active."""
class BenchExecutionError(BackupManagerError): """Raised when a bench command fails."""

@dataclass
class BackupConfig:
    site: str = "crm.localhost"
    test_site: str = "crm-test.localhost"
    bench_path: Path = Path("/home/frappe/frappe-bench")
    retention_count: int = 7
    db_root_password: str = os.getenv("FRAPPE_DB_ROOT_PASSWORD", "123")
    container_name: Optional[str] = "crm-frappe-1"

    @property
    def site_slug(self) -> str:
        """Frappe normalizes dots and dashes to underscores in backup filenames."""
        return self.site.replace(".", "_").replace("-", "_")

    @property
    def backup_dir(self) -> Path:
        """Directory where Frappe stores site backups."""
        return self.bench_path / "sites" / self.site / "private" / "backups"

class ProcessLock:
    """Guarantees only one instance runs at any given time using fcntl."""
    def __init__(self, lock_file_path: str = "/tmp/frappe_backup_manager.lock"):
        self.lock_file_path = lock_file_path
        self.fp = None

    def __enter__(self):
        self.fp = open(self.lock_file_path, "w")
        try:
            fcntl.flock(self.fp, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            raise LockAcquisitionError("Another backup instance is already running!")
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.fp:
            fcntl.flock(self.fp, fcntl.LOCK_UN)
            self.fp.close()

class BenchRunner:
    """Executes bench commands seamlessly whether running inside the container or on host."""
    def __init__(self, config: BackupConfig, logger: logging.Logger):
        self.config = config
        self.logger = logger
        self.is_native = shutil.which("bench") is not None

    def execute(self, bench_args: list[str]) -> subprocess.CompletedProcess:
        if self.is_native:
            cmd = ["bench"] + bench_args
        else:
            # Route through Docker container
            cmd = ["docker", "exec", "-w", str(self.config.bench_path), self.config.container_name, "bench"] + bench_args

        self.logger.debug(f"Executing: {' '.join(cmd)}")
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            self.logger.error(f"Command failed: {result.stderr.strip()}")
            raise BenchExecutionError(result.stderr.strip())
        return result
```

### 3. Verification Plan for Phase 1
- Run a dry CLI test to verify lock acquisition: launch two scripts simultaneously, assert the second exits cleanly with `LockAcquisitionError`.
- Verify `BenchRunner`: execute `runner.execute(["--version"])` and confirm it prints `5.31.1` across both native and Docker modes.

---

## Phase 2: Atomic Backup Set Discovery & Modeling

### 1. Intuition & Rationale
* **The Multi-Artifact Dilemma**: A single backup in Frappe is never just one file. It consists of:
  1. `YYYYMMDD_HHMMSS-<site>-database.sql.gz` (MariaDB dump)
  2. `YYYYMMDD_HHMMSS-<site>-files.tar` (Public files)
  3. `YYYYMMDD_HHMMSS-<site>-private-files.tar` (Private attachments)
  4. `YYYYMMDD_HHMMSS-<site>-site_config_backup.json` (Site configuration & encryption key)
  Plus our manifest files:
  5. `YYYYMMDD_HHMMSS-<site>-manifest.json`
  6. `YYYYMMDD_HHMMSS-<site>-checksums.sha256`
* **Why Timestamp Grouping is Essential**:
  All files from the same run share the identical 15-character timestamp prefix: `YYYYMMDD_HHMMSS`. 
  By parsing this prefix with regex, we group these loose files into a single conceptual `BackupSet` object.
* **The `is_complete` Guard**:
  If a backup run crashed halfway (e.g., only wrote the DB file before failing), that partial snapshot is flagged as `is_complete = False`. This prevents treating broken dumps as valid restore points.

### 2. Code Structure Blueprint (Phase 2)
```python
import re
from dataclasses import dataclass
from typing import Optional
from pathlib import Path

@dataclass
class BackupSet:
    timestamp: str
    site: str
    database: Optional[Path] = None
    public_files: Optional[Path] = None
    private_files: Optional[Path] = None
    site_config: Optional[Path] = None
    manifest: Optional[Path] = None
    checksum_file: Optional[Path] = None

    @property
    def core_artifacts(self) -> dict[str, Optional[Path]]:
        return {
            "database": self.database,
            "public_files": self.public_files,
            "private_files": self.private_files,
            "site_config": self.site_config,
        }

    @property
    def is_complete(self) -> bool:
        """True only if all 4 core Frappe artifacts exist on disk."""
        return all(p is not None and p.exists() for p in self.core_artifacts.values())

    @property
    def all_files(self) -> list[Path]:
        """Returns all present files belonging to this backup set."""
        return [p for p in [self.database, self.public_files, self.private_files, 
                            self.site_config, self.manifest, self.checksum_file] if p and p.exists()]

class BackupCatalog:
    """Discovers and parses backup sets from disk."""
    def __init__(self, config: BackupConfig, logger: logging.Logger):
        self.config = config
        self.logger = logger
        # Regex matching: 20261104_115904-crm_localhost-database.sql.gz
        self.pattern = re.compile(rf"^(\d{{8}}_\d{{6}})-{re.escape(self.config.site_slug)}-(.+)$")

    def discover_sets(self) -> dict[str, BackupSet]:
        catalog: dict[str, BackupSet] = {}
        # Resolve files on disk (either local or via container directory mapping)
        backup_dir = self.config.backup_dir
        if not backup_dir.exists():
            return catalog

        for entry in backup_dir.iterdir():
            match = self.pattern.match(entry.name)
            if not match:
                continue

            timestamp, suffix = match.group(1), match.group(2)
            if timestamp not in catalog:
                catalog[timestamp] = BackupSet(timestamp=timestamp, site=self.config.site)

            b_set = catalog[timestamp]
            if suffix == "database.sql.gz": b_set.database = entry
            elif suffix == "files.tar": b_set.public_files = entry
            elif suffix == "private-files.tar": b_set.private_files = entry
            elif suffix == "site_config_backup.json": b_set.site_config = entry
            elif suffix == "manifest.json": b_set.manifest = entry
            elif suffix == "checksums.sha256": b_set.checksum_file = entry

        return catalog
```

### 3. Verification Plan for Phase 2
- Run a `list` command: discover existing backup sets in `sites/crm.localhost/private/backups/`.
- Confirm that existing files with timestamp `20261104_115904` are grouped into a single `BackupSet` with `is_complete == True`.

---

## Phase 3: Two-Stage Deep Verification & Dual Manifest Engine

### 1. Intuition & Rationale
* **The Truncated Dump Trap**: Why is SHA-256 alone insufficient when generating a fresh backup?
  * If MariaDB terminates prematurely or disk space runs out mid-dump, `mysqldump` produces a partial, broken `.sql.gz` file.
  * If a script calculates SHA-256 immediately without checking structure, it registers a valid hash for a broken file!
  * **Solution (Stage A Structural Check)**:
    - `.sql.gz`: Stream to EOF with `gzip.open()`. This forces `zlib` to validate the **gzip trailer (CRC32 digest and uncompressed size)**. Any truncated stream raises `EOFError`.
    - `.tar`: Open with `tarfile.open()` and iterate `tar.getmembers()` to confirm tar headers are valid.
    - `site_config_backup.json`: `json.loads()` and assert keys `"db_name"` and `"db_password"` exist.
* **Stage B (Cryptographic Check)**:
  * Stream 64 KB binary chunks into `hashlib.sha256()`. Memory usage remains capped at 64 KB regardless of database size.
* **Dual Manifest Output**:
  1. `manifest.json`: Rich JSON with ISO-8601 timestamps, sizes, and file statuses.
  2. `checksums.sha256`: Standard Linux format (`<hash>  <filename>`) enabling verification with native `sha256sum -c`.

### 2. Code Structure Blueprint (Phase 3)
```python
import gzip
import json
import tarfile
import hashlib
from datetime import datetime, timezone

class VerificationError(BackupManagerError): """Raised when integrity validation fails."""

class IntegrityVerifier:
    """Performs structural archive validation, streaming SHA-256 calculation, and manifest creation."""
    def __init__(self, logger: logging.Logger):
        self.logger = logger

    def validate_structure(self, backup_set: BackupSet) -> None:
        """Stage A: Validates that files are structurally complete and not truncated."""
        # 1. Gzip Stream Validation
        if backup_set.database and backup_set.database.exists():
            try:
                with gzip.open(backup_set.database, "rb") as gz:
                    while gz.read(65536): pass  # Read through to trailer to trigger CRC32 validation
            except (gzip.BadGzipFile, EOFError, OSError) as e:
                raise VerificationError(f"Corrupt or truncated database gzip: {e}")

        # 2. Tar Archive Validation
        for tar_path in [backup_set.public_files, backup_set.private_files]:
            if tar_path and tar_path.exists():
                try:
                    with tarfile.open(tar_path, "r") as tar:
                        _ = tar.getmembers()
                except (tarfile.TarError, EOFError) as e:
                    raise VerificationError(f"Corrupt tar archive {tar_path.name}: {e}")

        # 3. JSON Config Validation
        if backup_set.site_config and backup_set.site_config.exists():
            try:
                data = json.loads(backup_set.site_config.read_text())
                if "db_name" not in data:
                    raise VerificationError("site_config missing 'db_name' key")
            except Exception as e:
                raise VerificationError(f"Invalid site_config JSON: {e}")

    def compute_sha256(self, file_path: Path) -> str:
        """Stage B: Calculates SHA-256 using 64 KB memory-safe chunks."""
        hasher = hashlib.sha256()
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(65536), b""):
                hasher.update(chunk)
        return hasher.hexdigest()

    def generate_manifests(self, backup_set: BackupSet, config: BackupConfig) -> None:
        """Writes both JSON manifest and standard Linux checksums.sha256."""
        self.validate_structure(backup_set)
        
        manifest_data = {
            "timestamp": backup_set.timestamp,
            "site": backup_set.site,
            "created_utc": datetime.now(timezone.utc).isoformat(),
            "status": "VERIFIED",
            "artifacts": {}
        }
        
        sha256_lines = []
        for name, path in backup_set.core_artifacts.items():
            if path and path.exists():
                checksum = self.compute_sha256(path)
                manifest_data["artifacts"][name] = {
                    "filename": path.name,
                    "size_bytes": path.stat().st_size,
                    "sha256": checksum
                }
                sha256_lines.append(f"{checksum}  {path.name}")

        # Save manifest.json
        manifest_path = config.backup_dir / f"{backup_set.timestamp}-{config.site_slug}-manifest.json"
        manifest_path.write_text(json.dumps(manifest_data, indent=2))
        backup_set.manifest = manifest_path

        # Save checksums.sha256
        sha_path = config.backup_dir / f"{backup_set.timestamp}-{config.site_slug}-checksums.sha256"
        sha_path.write_text("\n".join(sha256_lines) + "\n")
        backup_set.checksum_file = sha_path
        self.logger.info(f"Generated verified manifests for backup {backup_set.timestamp}")
```

### 3. Verification Plan for Phase 3
- Generate manifests for an existing backup set.
- Run `sha256sum -c <timestamp>-crm_localhost-checksums.sha256` in Linux to assert standard compatibility.
- Tamper with a test copy of a `.sql.gz` file (truncate last 10 bytes); assert `validate_structure()` catches it with `VerificationError`.

---

## Phase 4: Fault-Tolerant Retention Policy & Pruning

### 1. Intuition & Rationale
* **The Partial Backup Trap**: If a retention policy simply counts the 7 latest backups regardless of validity:
  * A series of failed backups (producing incomplete artifacts) would push healthy historical backups out of the retention window.
  * **Solution**: Filter `valid_sets = [s for s in sorted_sets if s.is_complete]`. Only complete snapshots count toward the retention quota of 7.
* **Atomic Deletion**: When an outdated snapshot is purged, all of its files (database, public files, private files, config, manifest, checksum file) must be removed simultaneously to leave zero orphaned files on disk.
* **Simulation Safety (`--dry-run`)**: Allow operators to see exactly which files and how many megabytes will be freed before committing the deletion.

### 2. Code Structure Blueprint (Phase 4)
```python
class RetentionPolicy:
    """Enforces retention by keeping the latest N complete backup sets."""
    def __init__(self, config: BackupConfig, catalog: BackupCatalog, logger: logging.Logger):
        self.config = config
        self.catalog = catalog
        self.logger = logger

    def prune(self, dry_run: bool = False) -> list[str]:
        sets = self.catalog.discover_sets()
        # Sort lexicographically descending (newest timestamp first)
        sorted_timestamps = sorted(sets.keys(), reverse=True)
        sorted_sets = [sets[t] for t in sorted_timestamps]

        # Only complete sets count toward the retention quota!
        valid_sets = [s for s in sorted_sets if s.is_complete]
        
        to_keep = valid_sets[:self.config.retention_count]
        to_prune = valid_sets[self.config.retention_count:]
        
        pruned_timestamps = []
        total_bytes_freed = 0

        for b_set in to_prune:
            self.logger.info(f"{'[DRY RUN] Would prune' if dry_run else 'Pruning'} backup set: {b_set.timestamp}")
            for file_path in b_set.all_files:
                file_size = file_path.stat().st_size
                total_bytes_freed += file_size
                if not dry_run:
                    file_path.unlink(missing_ok=True)
                    self.logger.debug(f"Deleted {file_path.name}")
            pruned_timestamps.append(b_set.timestamp)

        self.logger.info(f"Retention complete. Kept: {len(to_keep)}, Pruned: {len(to_prune)} ({total_bytes_freed / 1024 / 1024:.2f} MB)")
        return pruned_timestamps
```

### 3. Verification Plan for Phase 4
- Create 8 simulated backup directories or mock files.
- Run `prune --dry-run` and confirm it identifies only set #8 for deletion.
- Run `prune` live and confirm set #8 is deleted, leaving exactly the 7 newest intact.

---

## Phase 5: Disaster Recovery & Safe Test-Site Restoration

### 1. Intuition & Rationale
* **Pre-Flight Checksum Gate**: Never initiate a restore with an unverified backup. The script computes the hashes of the target backup set and verifies against `manifest.json` before touching the test site.
* **The Non-Existent Site Trap**: `bench restore` throws `Site crm-test.localhost does not exist!` if the directory doesn't exist. The script automatically bootstraps `crm-test.localhost` using `bench new-site` if missing.
* **Neutralizing the Schedulers (Crucial Safety Step)**:
  * When production data is restored into a test site, background RQ/Celery workers could pick up pending customer emails or webhook dispatches.
  * Running `bench --site crm-test.localhost scheduler disable` guarantees total isolation.
* **Selective `encryption_key` Splicing**:
  * Passwords and integration secrets in the database are encrypted with production's `encryption_key`.
  * The script reads `encryption_key` from `site_config_backup.json` and updates `sites/crm-test.localhost/site_config.json`, while **preserving the test site's unique `db_name` and `db_password`**.
* **ORM Smoke Test**:
  * Execute `bench --site crm-test.localhost execute frappe.db.count --args "['User']"` to confirm database connectivity, schema loading, and data presence.

### 2. Code Structure Blueprint (Phase 5)
```python
class RestoreManager:
    """Orchestrates verified disaster recovery restoration into an isolated test environment."""
    def __init__(self, config: BackupConfig, runner: BenchRunner, verifier: IntegrityVerifier, logger: logging.Logger):
        self.config = config
        self.runner = runner
        self.verifier = verifier
        self.logger = logger

    def restore_to_test_site(self, target_set: BackupSet) -> None:
        self.logger.info(f"Initiating restoration of backup {target_set.timestamp} to {self.config.test_site}")

        # 1. Pre-Flight Integrity Gate
        self.verifier.validate_structure(target_set)
        for name, path in target_set.core_artifacts.items():
            if path:
                self.logger.info(f"Pre-flight SHA-256 check passed for {name}: {path.name}")

        # 2. Site Existence & Bootstrap Check
        test_site_dir = self.config.bench_path / "sites" / self.config.test_site
        if not test_site_dir.exists():
            self.logger.info(f"Test site {self.config.test_site} does not exist. Bootstrapping...")
            self.runner.execute([
                "new-site", self.config.test_site,
                "--mariadb-root-password", self.config.db_root_password,
                "--admin-password", "admin",
                "--no-mariadb-socket"
            ])

        # 3. Execute Bench Restore
        restore_args = [
            "--site", self.config.test_site,
            "restore", str(target_set.database),
            "--mariadb-root-password", self.config.db_root_password,
            "--force"
        ]
        if target_set.public_files:
            restore_args.extend(["--with-public-files", str(target_set.public_files)])
        if target_set.private_files:
            restore_args.extend(["--with-private-files", str(target_set.private_files)])

        self.logger.info("Executing database and files restoration...")
        self.runner.execute(restore_args)

        # 4. Neutralize Background Schedulers (Safety Guard)
        self.logger.info("Disabling scheduler on test site to prevent email/webhook leaks...")
        self.runner.execute(["--site", self.config.test_site, "scheduler", "disable"])

        # 5. Splice Encryption Key into Test Site Config
        if target_set.site_config and target_set.site_config.exists():
            prod_config = json.loads(target_set.site_config.read_text())
            test_config_path = test_site_dir / "site_config.json"
            if test_config_path.exists() and "encryption_key" in prod_config:
                test_config = json.loads(test_config_path.read_text())
                test_config["encryption_key"] = prod_config["encryption_key"]
                test_config_path.write_text(json.dumps(test_config, indent=2))
                self.logger.info("Successfully spliced production encryption key into test site config.")

        # 6. Cache Clear & ORM Smoke Test
        self.runner.execute(["--site", self.config.test_site, "clear-cache"])
        smoke_result = self.runner.execute([
            "--site", self.config.test_site,
            "execute", "frappe.db.count",
            "--args", "['User']"
        ])
        user_count = int(smoke_result.stdout.strip())
        self.logger.info(f"Restoration Smoke Test PASSED! User count in test database: {user_count}")
```

---

## Phase-by-Phase Roadmap for Manual Implementation

```
┌──────────────────────────────────────────────────────────────┐
│ STEP 1: Phase 1 (Foundation & Runner)                ~25 mins│
│ • Write logging, ProcessLock, BackupConfig, BenchRunner      │
│ • Verify execution of bench version                          │
├──────────────────────────────────────────────────────────────┤
│ STEP 2: Phase 2 (Catalog & Grouping)                 ~20 mins│
│ • Write BackupSet, BackupCatalog with regex                  │
│ • Verify 'list' command against real backup directory        │
├──────────────────────────────────────────────────────────────┤
│ STEP 3: Phase 3 (Verification & Manifests)           ~30 mins│
│ • Write gzip trailer inspection and 64KB streaming SHA-256   │
│ • Test 'verify' and generate sample reports                  │
├──────────────────────────────────────────────────────────────┤
│ STEP 4: Phase 4 (Retention Policy)                   ~20 mins│
│ • Write RetentionPolicy with is_complete guard               │
│ • Test 'prune' with --dry-run and live pruning               │
├──────────────────────────────────────────────────────────────┤
│ STEP 5: Phase 5 (Restore & Disaster Recovery)        ~35 mins│
│ • Write RestoreManager, scheduler disabling, key splicing    │
│ • Test 'restore --test-site crm-test.localhost' & smoke test │
└──────────────────────────────────────────────────────────────┘
```

---

## Verification Plan

### Automated Test Steps
1. **Lock Verification**:
   ```bash
   python3 scripts/backup_manager.py backup &
   python3 scripts/backup_manager.py backup # Should immediately raise LockAcquisitionError
   ```
2. **Backup & Manifest Generation**:
   ```bash
   python3 scripts/backup_manager.py backup --site crm.localhost --verify
   ```
3. **Checksum Verification**:
   ```bash
   python3 scripts/backup_manager.py verify --site crm.localhost
   sha256sum -c sites/crm.localhost/private/backups/*-checksums.sha256
   ```
4. **Retention Boundary Pruning**:
   ```bash
   python3 scripts/backup_manager.py prune --site crm.localhost --retention 7 --dry-run
   ```
5. **Test Site Recovery**:
   ```bash
   python3 scripts/backup_manager.py restore --site crm.localhost --test-site crm-test.localhost --db-root-password 123
   ```
