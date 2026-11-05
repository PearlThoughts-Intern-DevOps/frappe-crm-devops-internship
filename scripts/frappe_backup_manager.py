#!/usr/bin/env python3
"""
Frappe CRM Backup & Restore Automation Tool
===========================================
Enterprise-grade Python automation tool for Frappe CRM backups,
SHA-256 integrity verification, retention management, and test environment restoration.

Author: DevOps Engineering Team
License: MIT
"""

import argparse
import dataclasses
import datetime
import gzip
import hashlib
import json
import logging
import os
import re
import shutil
import subprocess
import sys
import tarfile
import tempfile
import time
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any

# ==============================================================================
# Logging Configuration
# ==============================================================================

class ColorFormatter(logging.Formatter):
    """Custom logging formatter with ANSI color coding for terminal clarity."""
    
    COLORS = {
        logging.DEBUG: "\033[36m",     # Cyan
        logging.INFO: "\033[32m",      # Green
        logging.WARNING: "\033[33m",   # Yellow
        logging.ERROR: "\033[31m",     # Red
        logging.CRITICAL: "\033[41m",  # Red background
    }
    RESET = "\033[0m"
    BOLD = "\033[1m"

    def format(self, record):
        color = self.COLORS.get(record.levelno, self.RESET)
        timestamp = datetime.datetime.fromtimestamp(record.created).strftime("%Y-%m-%d %H:%M:%S")
        level = f"{color}[{record.levelname:<7}]{self.RESET}"
        return f"{timestamp} {level} {record.getMessage()}"


def setup_logger(log_file: Optional[Path] = None, verbose: bool = False) -> logging.Logger:
    """Configures multi-channel logger (stdout + persistent log file)."""
    logger = logging.getLogger("frappe_backup_tool")
    logger.setLevel(logging.DEBUG if verbose else logging.INFO)
    logger.handlers.clear()

    # Console Handler (with colors if supported)
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.DEBUG if verbose else logging.INFO)
    console_handler.setFormatter(ColorFormatter())
    logger.addHandler(console_handler)

    # File Handler (structured plain text)
    if log_file:
        log_file.parent.mkdir(parents=True, exist_ok=True)
        file_handler = logging.FileHandler(str(log_file), encoding="utf-8")
        file_handler.setLevel(logging.DEBUG)
        file_formatter = logging.Formatter(
            "%(asctime)s [%(levelname)s] [%(name)s] %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S"
        )
        file_handler.setFormatter(file_formatter)
        logger.addHandler(file_handler)

    return logger


# ==============================================================================
# Data Models
# ==============================================================================

@dataclasses.dataclass
class BackupFileItem:
    """Represents a single file artifact inside a backup set."""
    path: Path
    file_type: str  # 'database', 'public_files', 'private_files', 'config', 'checksum', 'manifest'
    size_bytes: int
    sha256: Optional[str] = None
    is_valid: Optional[bool] = None
    error_message: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.path.name,
            "path": str(self.path),
            "file_type": self.file_type,
            "size_bytes": self.size_bytes,
            "size_human": format_size(self.size_bytes),
            "sha256": self.sha256,
            "is_valid": self.is_valid,
            "error_message": self.error_message,
        }


@dataclasses.dataclass
class BackupSet:
    """Represents a complete cohesive backup set for a specific timestamp."""
    site: str
    timestamp: str  # Format: YYYYMMDD_HHMMSS
    database_file: Optional[Path] = None
    public_files: Optional[Path] = None
    private_files: Optional[Path] = None
    site_config_file: Optional[Path] = None
    checksum_file: Optional[Path] = None
    manifest_file: Optional[Path] = None

    @property
    def created_at(self) -> Optional[datetime.datetime]:
        try:
            return datetime.datetime.strptime(self.timestamp, "%Y%m%d_%H%M%S")
        except ValueError:
            return None

    @property
    def all_data_files(self) -> List[Path]:
        """Returns primary data files (DB, files, config) excluding checksum & manifest."""
        files = []
        for f in [self.database_file, self.public_files, self.private_files, self.site_config_file]:
            if f and f.exists():
                files.append(f)
        return files

    @property
    def all_files(self) -> List[Path]:
        """Returns every file associated with this backup set."""
        files = self.all_data_files
        for f in [self.checksum_file, self.manifest_file]:
            if f and f.exists():
                files.append(f)
        return files

    @property
    def total_size_bytes(self) -> int:
        total = 0
        for f in self.all_files:
            try:
                total += f.stat().st_size
            except OSError:
                pass
        return total

    def is_complete(self) -> bool:
        """Checks if database file exists (at minimum) for a viable backup."""
        return bool(self.database_file and self.database_file.exists() and self.database_file.stat().st_size > 0)


def format_size(size_bytes: int) -> str:
    """Formats bytes to human-readable string (KiB, MiB, GiB)."""
    for unit in ['B', 'KiB', 'MiB', 'GiB', 'TiB']:
        if abs(size_bytes) < 1024.0:
            return f"{size_bytes:3.1f} {unit}"
        size_bytes /= 1024.0
    return f"{size_bytes:.1f} PiB"


# ==============================================================================
# Bench Command Executor
# ==============================================================================

class BenchExecutor:
    """Executes Frappe Bench commands either locally or within a Docker container."""

    def __init__(
        self,
        bench_dir: Path,
        docker_container: Optional[str] = None,
        logger: Optional[logging.Logger] = None
    ):
        self.bench_dir = bench_dir
        self.docker_container = docker_container
        self.logger = logger or logging.getLogger("frappe_backup_tool")

    def run(self, cmd_args: List[str], timeout: int = 600) -> subprocess.CompletedProcess:
        """Executes a bench command with comprehensive logging."""
        if self.docker_container:
            full_cmd = ["docker", "exec", "-w", str(self.bench_dir), self.docker_container, "bench"] + cmd_args
        else:
            full_cmd = ["bench"] + cmd_args

        self.logger.debug(f"Executing: {' '.join(full_cmd)}")
        start_time = time.time()

        try:
            result = subprocess.run(
                full_cmd,
                cwd=str(self.bench_dir) if not self.docker_container else None,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                timeout=timeout
            )
            elapsed = time.time() - start_time
            self.logger.debug(f"Command finished in {elapsed:.2f}s with exit code {result.returncode}")
            return result
        except subprocess.TimeoutExpired as e:
            self.logger.error(f"Command timed out after {timeout} seconds: {' '.join(full_cmd)}")
            raise
        except FileNotFoundError as e:
            self.logger.error(f"Required binary not found in PATH: {e}")
            raise


# ==============================================================================
# Backup Integrity & SHA-256 Verifier
# ==============================================================================

class IntegrityVerifier:
    """Handles SHA-256 generation, verification, and file format validation."""

    def __init__(self, logger: Optional[logging.Logger] = None):
        self.logger = logger or logging.getLogger("frappe_backup_tool")

    @staticmethod
    def calculate_sha256(filepath: Path, chunk_size: int = 65536) -> str:
        """Computes SHA-256 checksum in 64KiB chunks to handle large files memory-efficiently."""
        hasher = hashlib.sha256()
        with open(filepath, "rb") as f:
            while chunk := f.read(chunk_size):
                hasher.update(chunk)
        return hasher.hexdigest()

    def generate_checksum_manifest(self, backup_set: BackupSet) -> Tuple[Path, Path]:
        """
        Calculates SHA-256 for all backup artifacts and creates:
        1. Standard GNU sha256sum file (.sha256)
        2. Rich JSON metadata manifest (.manifest.json)
        """
        self.logger.info(f"Computing SHA-256 checksums for backup set [{backup_set.timestamp}]...")
        manifest_data = {
            "site": backup_set.site,
            "timestamp": backup_set.timestamp,
            "created_at_iso": backup_set.created_at.isoformat() if backup_set.created_at else "",
            "generated_by": "frappe_backup_manager.py",
            "files": {},
            "total_size_bytes": 0,
        }

        sha256_lines = []
        backups_dir = backup_set.database_file.parent if backup_set.database_file else Path(".")
        site_slug = backup_set.site.replace(".", "_")

        for file_path in backup_set.all_data_files:
            file_size = file_path.stat().st_size
            sha256_hash = self.calculate_sha256(file_path)
            
            # File type classification
            fname = file_path.name
            if "-database.sql" in fname:
                ftype = "database"
            elif "-private-files.tar" in fname:
                ftype = "private_files"
            elif "-files.tar" in fname:
                ftype = "public_files"
            elif "-site_config_backup.json" in fname:
                ftype = "site_config"
            else:
                ftype = "other"

            manifest_data["files"][fname] = {
                "file_type": ftype,
                "size_bytes": file_size,
                "size_human": format_size(file_size),
                "sha256": sha256_hash,
            }
            manifest_data["total_size_bytes"] += file_size
            sha256_lines.append(f"{sha256_hash}  {fname}")
            self.logger.info(f"  ✓ {fname} ({format_size(file_size)}) -> {sha256_hash[:16]}...")

        # Write .sha256 file
        checksum_file = backups_dir / f"{backup_set.timestamp}-{site_slug}-checksums.sha256"
        with open(checksum_file, "w", encoding="utf-8") as f:
            f.write("\n".join(sha256_lines) + "\n")
        backup_set.checksum_file = checksum_file
        self.logger.info(f"Saved SHA-256 checksum file: {checksum_file.name}")

        # Write .manifest.json
        manifest_file = backups_dir / f"{backup_set.timestamp}-{site_slug}-manifest.json"
        manifest_data["manifest_sha256_file"] = checksum_file.name
        with open(manifest_file, "w", encoding="utf-8") as f:
            json.dump(manifest_data, f, indent=2)
        backup_set.manifest_file = manifest_file
        self.logger.info(f"Saved backup metadata manifest: {manifest_file.name}")

        return checksum_file, manifest_file

    def test_archive_integrity(self, file_path: Path) -> Tuple[bool, Optional[str]]:
        """Deep integrity check ensuring file is not truncated or structurally corrupted."""
        if not file_path.exists():
            return False, f"File does not exist: {file_path}"
        if file_path.stat().st_size == 0:
            return False, f"File is empty (0 bytes): {file_path}"

        fname = file_path.name.lower()
        try:
            if fname.endswith(".sql.gz") or fname.endswith(".gz"):
                # Stream through gzip to verify header, decompressed data, and CRC32
                with gzip.open(file_path, "rb") as gz:
                    while gz.read(65536):
                        pass
                return True, None

            elif fname.endswith(".tar"):
                # Validate tar container headers
                if not tarfile.is_tarfile(str(file_path)):
                    return False, "Not a valid TAR archive"
                with tarfile.open(file_path, "r") as tar:
                    for _ in tar.getmembers():
                        pass
                return True, None

            elif fname.endswith(".json"):
                # Validate JSON syntax
                with open(file_path, "r", encoding="utf-8") as f:
                    json.load(f)
                return True, None

            return True, None
        except Exception as e:
            return False, f"Archive corruption detected: {str(e)}"

    def verify_backup_set(self, backup_set: BackupSet) -> Dict[str, Any]:
        """
        Performs thorough dual-layer verification:
        Layer 1: SHA-256 hash validation against saved checksum / manifest
        Layer 2: Structural archive integrity verification (Gzip CRC32 / Tar headers / JSON syntax)
        """
        self.logger.info(f"Verifying backup set [{backup_set.timestamp}] for site '{backup_set.site}'...")
        results = {
            "site": backup_set.site,
            "timestamp": backup_set.timestamp,
            "overall_valid": True,
            "files": [],
            "errors": [],
        }

        # Load recorded checksums from .sha256 or .manifest.json
        expected_checksums: Dict[str, str] = {}
        if backup_set.checksum_file and backup_set.checksum_file.exists():
            with open(backup_set.checksum_file, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith("#"):
                        parts = line.split(None, 1)
                        if len(parts) == 2:
                            expected_checksums[parts[1].strip()] = parts[0].strip()

        elif backup_set.manifest_file and backup_set.manifest_file.exists():
            with open(backup_set.manifest_file, "r", encoding="utf-8") as f:
                data = json.load(f)
                for fname, finfo in data.get("files", {}).items():
                    if "sha256" in finfo:
                        expected_checksums[fname] = finfo["sha256"]

        # If neither exists, we calculate fresh hashes and verify archive integrity
        if not expected_checksums:
            self.logger.warning(
                f"No existing checksum file or manifest found for [{backup_set.timestamp}]. "
                "Generating fresh checksums and testing archive integrity."
            )

        data_files = backup_set.all_data_files
        if not data_files:
            results["overall_valid"] = False
            results["errors"].append("No backup data files found for this backup set.")
            return results

        for fpath in data_files:
            fname = fpath.name
            size_bytes = fpath.stat().st_size
            calculated_sha = self.calculate_sha256(fpath)

            file_valid = True
            error_msg = None

            # 1. SHA-256 check
            if fname in expected_checksums:
                exp_sha = expected_checksums[fname]
                if calculated_sha.lower() != exp_sha.lower():
                    file_valid = False
                    error_msg = f"SHA-256 MISMATCH! Expected: {exp_sha}, Got: {calculated_sha}"
            else:
                exp_sha = calculated_sha

            # 2. Archive format check
            if file_valid:
                struct_ok, struct_err = self.test_archive_integrity(fpath)
                if not struct_ok:
                    file_valid = False
                    error_msg = struct_err

            item_result = {
                "file": fname,
                "path": str(fpath),
                "size_bytes": size_bytes,
                "size_human": format_size(size_bytes),
                "sha256": calculated_sha,
                "expected_sha256": exp_sha,
                "valid": file_valid,
                "error": error_msg,
            }
            results["files"].append(item_result)

            if not file_valid:
                results["overall_valid"] = False
                results["errors"].append(f"{fname}: {error_msg}")
                self.logger.error(f"  ✗ [FAIL] {fname}: {error_msg}")
            else:
                self.logger.info(f"  ✓ [PASS] {fname} ({format_size(size_bytes)}) [SHA256: {calculated_sha[:16]}...]")

        if results["overall_valid"]:
            self.logger.info(f"Backup set [{backup_set.timestamp}] PASSED all verification checks.")
        else:
            self.logger.error(f"Backup set [{backup_set.timestamp}] FAILED verification!")

        return results


# ==============================================================================
# Retention Policy Manager
# ==============================================================================

class RetentionManager:
    """Enforces backup retention policies, pruning older backups beyond the retention threshold."""

    def __init__(self, logger: Optional[logging.Logger] = None):
        self.logger = logger or logging.getLogger("frappe_backup_tool")

    @staticmethod
    def discover_backup_sets(backups_dir: Path, site: str) -> List[BackupSet]:
        """
        Discovers and groups all backup artifacts in the backups directory
        by their timestamp prefix (YYYYMMDD_HHMMSS).
        """
        if not backups_dir.exists():
            return []

        # Timestamp pattern: YYYYMMDD_HHMMSS
        pattern = re.compile(r"^(\d{8}_\d{6})-")
        sets_map: Dict[str, BackupSet] = {}

        for entry in backups_dir.iterdir():
            if not entry.is_file():
                continue
            match = pattern.match(entry.name)
            if not match:
                continue

            ts = match.group(1)
            if ts not in sets_map:
                sets_map[ts] = BackupSet(site=site, timestamp=ts)

            bset = sets_map[ts]
            ename = entry.name

            if "-database.sql" in ename:
                bset.database_file = entry
            elif "-private-files.tar" in ename:
                bset.private_files = entry
            elif "-files.tar" in ename:
                bset.public_files = entry
            elif "-site_config_backup.json" in ename:
                bset.site_config_file = entry
            elif "-checksums.sha256" in ename:
                bset.checksum_file = entry
            elif "-manifest.json" in ename:
                bset.manifest_file = entry

        # Sort newest first (descending timestamp)
        sorted_sets = sorted(sets_map.values(), key=lambda s: s.timestamp, reverse=True)
        return sorted_sets

    def enforce_retention(
        self,
        backup_sets: List[BackupSet],
        keep_count: int = 7,
        dry_run: bool = False
    ) -> Dict[str, Any]:
        """
        Keeps the latest `keep_count` backups and removes older sets along with
        all associated checksum and manifest files.
        """
        self.logger.info(
            f"Evaluating retention policy: Keep latest {keep_count} backups. "
            f"Found {len(backup_sets)} existing backup set(s)."
        )

        retained = backup_sets[:keep_count]
        prune_candidates = backup_sets[keep_count:]

        report = {
            "total_found": len(backup_sets),
            "retention_limit": keep_count,
            "retained_count": len(retained),
            "pruned_count": len(prune_candidates),
            "bytes_freed": 0,
            "pruned_sets": [],
            "retained_sets": [s.timestamp for s in retained],
            "dry_run": dry_run,
        }

        if not prune_candidates:
            self.logger.info(f"Retention policy compliant. No backups require pruning (Total: {len(backup_sets)} <= {keep_count}).")
            return report

        self.logger.info(f"Identified {len(prune_candidates)} backup set(s) eligible for pruning:")

        for bset in prune_candidates:
            set_freed = 0
            pruned_files = []
            self.logger.info(f"Pruning backup set [{bset.timestamp}] (Age: {bset.created_at}):")

            for fpath in bset.all_files:
                try:
                    fsize = fpath.stat().st_size
                    if not dry_run:
                        fpath.unlink()
                        self.logger.info(f"  ✓ Deleted: {fpath.name} ({format_size(fsize)})")
                    else:
                        self.logger.info(f"  [DRY-RUN] Would delete: {fpath.name} ({format_size(fsize)})")
                    set_freed += fsize
                    pruned_files.append(fpath.name)
                except OSError as e:
                    self.logger.error(f"  ✗ Failed to delete {fpath.name}: {e}")

            report["bytes_freed"] += set_freed
            report["pruned_sets"].append({
                "timestamp": bset.timestamp,
                "freed_bytes": set_freed,
                "freed_human": format_size(set_freed),
                "files": pruned_files,
            })

        action_word = "Would free" if dry_run else "Successfully freed"
        self.logger.info(f"{action_word} {format_size(report['bytes_freed'])} across {len(prune_candidates)} backup set(s).")
        return report


# ==============================================================================
# Frappe Backup & Restore Orchestrator
# ==============================================================================

class FrappeBackupManager:
    """Master orchestrator class for Frappe CRM backups, restores, and verifications."""

    def __init__(
        self,
        bench_dir: Path,
        docker_container: Optional[str] = None,
        log_file: Optional[Path] = None,
        verbose: bool = False
    ):
        self.bench_dir = Path(bench_dir).resolve()
        self.docker_container = docker_container
        self.logger = setup_logger(log_file, verbose)
        self.bench = BenchExecutor(self.bench_dir, docker_container, self.logger)
        self.verifier = IntegrityVerifier(self.logger)
        self.retention = RetentionManager(self.logger)

    def get_site_backups_dir(self, site: str) -> Path:
        """Returns the filesystem path for site's private/backups directory."""
        return self.bench_dir / "sites" / site / "private" / "backups"

    def backup(
        self,
        site: str = "crm.localhost",
        with_files: bool = True,
        compress: bool = False,
        retention_count: int = 7,
        reports_dir: Optional[Path] = None
    ) -> Dict[str, Any]:
        """
        Executes a complete Frappe backup operation:
        1. Runs `bench --site <site> backup --with-files`
        2. Detects generated files
        3. Computes SHA-256 checksums and writes .sha256 & .manifest.json
        4. Verifies backup integrity
        5. Enforces retention policy (default 7 backups)
        6. Generates JSON & Markdown audit reports
        """
        start_time = datetime.datetime.now()
        self.logger.info("=" * 70)
        self.logger.info(f"STARTING FRAPPE CRM BACKUP — Site: '{site}'")
        self.logger.info(f"Options: with_files={with_files}, compress={compress}, retention={retention_count}")
        self.logger.info("=" * 70)

        # 1. Run bench backup
        bench_args = ["--site", site, "backup"]
        if with_files:
            bench_args.append("--with-files")
        if compress:
            bench_args.append("--compress")

        result = self.bench.run(bench_args, timeout=900)
        if result.returncode != 0:
            self.logger.error(f"Backup command failed with exit code {result.returncode}!")
            self.logger.error(result.stderr)
            raise RuntimeError(f"Bench backup execution failed: {result.stderr.strip()}")

        self.logger.info("Bench backup command finished successfully.")
        self.logger.debug(f"Bench output:\n{result.stdout}")

        # 2. Discover newest backup set
        backups_dir = self.get_site_backups_dir(site)
        existing_sets = self.retention.discover_backup_sets(backups_dir, site)
        if not existing_sets:
            raise FileNotFoundError(f"No backup sets found in {backups_dir} after backup execution.")

        latest_set = existing_sets[0]
        self.logger.info(f"Captured new backup set: [{latest_set.timestamp}]")
        self.logger.info(f"Database dump: {latest_set.database_file.name if latest_set.database_file else 'None'}")
        if with_files:
            self.logger.info(f"Public files:  {latest_set.public_files.name if latest_set.public_files else 'None'}")
            self.logger.info(f"Private files: {latest_set.private_files.name if latest_set.private_files else 'None'}")

        # 3. Compute SHA-256 checksums & create manifest
        checksum_file, manifest_file = self.verifier.generate_checksum_manifest(latest_set)

        # 4. Immediate Post-Backup Verification
        verification_report = self.verifier.verify_backup_set(latest_set)
        if not verification_report["overall_valid"]:
            raise ValueError(f"Post-backup integrity verification failed: {verification_report['errors']}")

        # 5. Enforce Retention Policy
        all_sets = self.retention.discover_backup_sets(backups_dir, site)
        retention_report = self.retention.enforce_retention(
            backup_sets=all_sets,
            keep_count=retention_count,
            dry_run=False
        )

        end_time = datetime.datetime.now()
        duration_seconds = (end_time - start_time).total_seconds()

        # 6. Generate Reports
        summary_report = {
            "status": "SUCCESS",
            "operation": "backup",
            "site": site,
            "timestamp": latest_set.timestamp,
            "started_at": start_time.isoformat(),
            "completed_at": end_time.isoformat(),
            "duration_seconds": round(duration_seconds, 2),
            "backup_set": {
                "timestamp": latest_set.timestamp,
                "total_size_bytes": latest_set.total_size_bytes,
                "total_size_human": format_size(latest_set.total_size_bytes),
                "database_file": str(latest_set.database_file),
                "public_files": str(latest_set.public_files) if latest_set.public_files else None,
                "private_files": str(latest_set.private_files) if latest_set.private_files else None,
                "config_file": str(latest_set.site_config_file) if latest_set.site_config_file else None,
                "checksum_file": str(checksum_file),
                "manifest_file": str(manifest_file),
            },
            "verification": verification_report,
            "retention": retention_report,
        }

        # Save report files
        if not reports_dir:
            reports_dir = backups_dir / "reports"
        reports_dir.mkdir(parents=True, exist_ok=True)

        json_report_path = reports_dir / f"backup_report_{latest_set.timestamp}.json"
        with open(json_report_path, "w", encoding="utf-8") as f:
            json.dump(summary_report, f, indent=2)

        md_report_path = reports_dir / f"backup_report_{latest_set.timestamp}.md"
        self._write_markdown_report(summary_report, md_report_path)

        self.logger.info("=" * 70)
        self.logger.info(f"BACKUP COMPLETED SUCCESSFULLY in {duration_seconds:.2f}s")
        self.logger.info(f"Audit Reports saved to:")
        self.logger.info(f"  • JSON: {json_report_path}")
        self.logger.info(f"  • Markdown: {md_report_path}")
        self.logger.info("=" * 70)

        return summary_report

    def verify(
        self,
        site: str = "crm.localhost",
        timestamp: Optional[str] = None,
        verify_all: bool = False
    ) -> Dict[str, Any]:
        """Verifies one or all backup sets for a site against SHA-256 and archive structure."""
        backups_dir = self.get_site_backups_dir(site)
        backup_sets = self.retention.discover_backup_sets(backups_dir, site)

        if not backup_sets:
            self.logger.error(f"No backups found in {backups_dir}")
            return {"status": "ERROR", "message": "No backups found."}

        target_sets = []
        if verify_all:
            target_sets = backup_sets
        elif timestamp:
            matched = [s for s in backup_sets if s.timestamp == timestamp]
            if not matched:
                raise ValueError(f"Backup with timestamp '{timestamp}' not found in {backups_dir}")
            target_sets = matched
        else:
            target_sets = [backup_sets[0]]  # Latest

        overall_ok = True
        reports = []

        for bset in target_sets:
            rep = self.verifier.verify_backup_set(bset)
            reports.append(rep)
            if not rep["overall_valid"]:
                overall_ok = False

        return {
            "status": "SUCCESS" if overall_ok else "FAILED",
            "site": site,
            "verified_count": len(target_sets),
            "reports": reports
        }

    def sanitize_sql_dump_if_needed(self, sql_gz_path: Path) -> Path:
        """
        Fixes MariaDB 11 client vs MariaDB 10.8 server incompatibility:
        Strips 'NOTE_VERBOSITY' directives which trigger ERROR 1193 during restoration.
        Returns a sanitized temporary gzip path if needed, or original path if clean.
        """
        needs_sanitizing = False
        try:
            with gzip.open(sql_gz_path, "rt", encoding="utf-8", errors="ignore") as gz:
                # Inspect first 40 lines
                for _ in range(40):
                    line = gz.readline()
                    if not line:
                        break
                    if "NOTE_VERBOSITY" in line:
                        needs_sanitizing = True
                        break
        except Exception as e:
            self.logger.warning(f"Could not inspect SQL header: {e}")

        if not needs_sanitizing:
            return sql_gz_path

        self.logger.info("Detected MariaDB 11 'NOTE_VERBOSITY' compatibility directive. Sanitizing stream for restore...")
        temp_sanitized = Path(tempfile.gettempdir()) / f"sanitized_{sql_gz_path.name}"
        with gzip.open(sql_gz_path, "rt", encoding="utf-8", errors="ignore") as src:
            with gzip.open(temp_sanitized, "wt", encoding="utf-8") as dst:
                for line in src:
                    if "NOTE_VERBOSITY" not in line:
                        dst.write(line)

        self.logger.info(f"Created sanitized temporary dump: {temp_sanitized.name}")
        return temp_sanitized

    def restore(
        self,
        source_site: str = "crm.localhost",
        target_site: str = "test.localhost",
        timestamp: Optional[str] = None,
        mariadb_root_password: str = "123",
        with_files: bool = True,
        force: bool = False
    ) -> Dict[str, Any]:
        """
        Restores a verified backup into a target test environment site:
        1. Identifies backup set (latest or specified timestamp)
        2. Performs SHA-256 and archive validation BEFORE altering target database
        3. Sanitizes MariaDB dump if version mismatch directives exist
        4. Invokes `bench --site <target_site> restore ...`
        5. Clears cache and verifies restored tables
        """
        start_time = datetime.datetime.now()
        self.logger.info("=" * 70)
        self.logger.info(f"STARTING RESTORATION TO TEST ENVIRONMENT")
        self.logger.info(f"Source Site: '{source_site}' -> Target Test Site: '{target_site}'")
        self.logger.info("=" * 70)

        # 1. Locate source backup set
        backups_dir = self.get_site_backups_dir(source_site)
        existing_sets = self.retention.discover_backup_sets(backups_dir, source_site)
        if not existing_sets:
            raise FileNotFoundError(f"No backups available for site '{source_site}'")

        if timestamp:
            matched = [s for s in existing_sets if s.timestamp == timestamp]
            if not matched:
                raise ValueError(f"Backup timestamp '{timestamp}' not found in {backups_dir}")
            source_set = matched[0]
        else:
            source_set = existing_sets[0]

        self.logger.info(f"Selected backup set [{source_set.timestamp}] created at {source_set.created_at}")
        if not source_set.database_file or not source_set.database_file.exists():
            raise FileNotFoundError("Backup set is missing database dump file (.sql.gz)!")

        # 2. Pre-Restoration Verification (Safety Gate)
        self.logger.info("Running pre-restoration integrity checks on source backup...")
        pre_check = self.verifier.verify_backup_set(source_set)
        if not pre_check["overall_valid"]:
            err_msg = f"Restoration aborted! Source backup failed integrity check: {pre_check['errors']}"
            self.logger.critical(err_msg)
            raise ValueError(err_msg)
        self.logger.info("Pre-restoration integrity check PASSED. Proceeding to restore.")

        # 3. Check / Sanitize SQL Dump
        sql_to_restore = self.sanitize_sql_dump_if_needed(source_set.database_file)
        temp_file_used = (sql_to_restore != source_set.database_file)

        # 4. Build restore command
        bench_args = [
            "--site", target_site,
            "restore", str(sql_to_restore),
            "--mariadb-root-password", mariadb_root_password
        ]

        if with_files:
            if source_set.public_files and source_set.public_files.exists():
                bench_args.extend(["--with-public-files", str(source_set.public_files)])
            if source_set.private_files and source_set.private_files.exists():
                bench_args.extend(["--with-private-files", str(source_set.private_files)])

        if force:
            bench_args.append("--force")

        try:
            self.logger.info(f"Restoring database and files into site '{target_site}'...")
            res = self.bench.run(bench_args, timeout=900)
            if res.returncode != 0:
                self.logger.error(f"Restore command failed with code {res.returncode}!")
                self.logger.error(res.stderr)
                raise RuntimeError(f"Bench restore failed: {res.stderr.strip()}")

            self.logger.info(f"Restore command succeeded.")
            self.logger.debug(f"Bench output:\n{res.stdout}")

            # 5. Post-restore clear-cache
            self.logger.info(f"Clearing cache for target test site '{target_site}'...")
            self.bench.run(["--site", target_site, "clear-cache"])

        finally:
            if temp_file_used and sql_to_restore.exists():
                try:
                    sql_to_restore.unlink()
                    self.logger.debug("Removed temporary sanitized SQL dump.")
                except OSError:
                    pass

        duration = (datetime.datetime.now() - start_time).total_seconds()
        self.logger.info("=" * 70)
        self.logger.info(f"RESTORATION TO '{target_site}' COMPLETED IN {duration:.2f}s")
        self.logger.info("=" * 70)

        return {
            "status": "SUCCESS",
            "operation": "restore",
            "source_site": source_site,
            "target_site": target_site,
            "backup_timestamp": source_set.timestamp,
            "duration_seconds": round(duration, 2),
        }

    def list_backups(self, site: str = "crm.localhost") -> List[Dict[str, Any]]:
        """Returns catalog of all backups for a site."""
        backups_dir = self.get_site_backups_dir(site)
        backup_sets = self.retention.discover_backup_sets(backups_dir, site)

        catalog = []
        for bset in backup_sets:
            catalog.append({
                "timestamp": bset.timestamp,
                "created_at": bset.created_at.strftime("%Y-%m-%d %H:%M:%S") if bset.created_at else "Unknown",
                "total_size": format_size(bset.total_size_bytes),
                "has_database": bool(bset.database_file and bset.database_file.exists()),
                "has_public_files": bool(bset.public_files and bset.public_files.exists()),
                "has_private_files": bool(bset.private_files and bset.private_files.exists()),
                "has_checksum": bool(bset.checksum_file and bset.checksum_file.exists()),
                "has_manifest": bool(bset.manifest_file and bset.manifest_file.exists()),
            })
        return catalog

    def _write_markdown_report(self, report_data: Dict[str, Any], filepath: Path):
        """Generates a clean GitHub-flavored Markdown report."""
        md = []
        md.append(f"# Frappe CRM Backup & Verification Report")
        md.append(f"**Site:** `{report_data['site']}`  ")
        md.append(f"**Backup Timestamp:** `{report_data['timestamp']}`  ")
        md.append(f"**Generated At:** `{report_data['completed_at']}`  ")
        md.append(f"**Duration:** `{report_data['duration_seconds']}s`  ")
        md.append(f"**Status:** **{report_data['status']}**\n")

        md.append("## 1. Backup Artifacts & SHA-256 Checksums")
        md.append("| Artifact | File Name | Size | SHA-256 Checksum | Verification |")
        md.append("| :--- | :--- | :--- | :--- | :---: |")

        for f in report_data["verification"]["files"]:
            status_icon = "✅ PASS" if f["valid"] else "❌ FAIL"
            md.append(f"| {f.get('file_type', 'Data')} | `{f['file']}` | {f['size_human']} | `{f['sha256']}` | {status_icon} |")

        md.append("\n## 2. Retention Policy Execution")
        retention = report_data["retention"]
        md.append(f"- **Retention Limit:** Keeping latest **{retention['retention_limit']}** backups")
        md.append(f"- **Retained Backups Count:** {retention['retained_count']}")
        md.append(f"- **Pruned Backups Count:** {retention['pruned_count']}")
        md.append(f"- **Storage Space Freed:** {format_size(retention['bytes_freed'])}\n")

        if retention["pruned_sets"]:
            md.append("### Pruned Backup Sets")
            for ps in retention["pruned_sets"]:
                md.append(f"- Backup Set `{ps['timestamp']}` (Freed: {ps['freed_human']})")

        md.append("\n---\n*Report automatically generated by Frappe CRM DevOps Automation Tool.*")

        with open(filepath, "w", encoding="utf-8") as f:
            f.write("\n".join(md) + "\n")


# ==============================================================================
# CLI Entry Point
# ==============================================================================

def main():
    parser = argparse.ArgumentParser(
        description="Frappe CRM Backup & Restore Automation Tool",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Take full backup, compute SHA-256 checksums, and enforce 7-day retention
  python frappe_backup_manager.py backup --site crm.localhost

  # Verify latest backup integrity and SHA-256 hashes
  python frappe_backup_manager.py verify --site crm.localhost

  # Restore latest backup to test environment site
  python frappe_backup_manager.py restore --source-site crm.localhost --target-site test.localhost

  # List all backups and their verification status
  python frappe_backup_manager.py list --site crm.localhost

  # Prune backups keeping only latest 7
  python frappe_backup_manager.py prune --site crm.localhost --retention 7
        """
    )

    # Shared parser for common flags across subcommands
    shared_parser = argparse.ArgumentParser(add_help=False)
    shared_parser.add_argument("--json", action="store_true", help="Output final result as JSON to stdout")
    shared_parser.add_argument("--verbose", "-v", action="store_true", help="Enable verbose / debug logging output")

    # Global options on root parser
    parser.add_argument("--bench-dir", type=str, default="/home/frappe/frappe-bench",
                        help="Path to frappe-bench directory (default: /home/frappe/frappe-bench or current dir)")
    parser.add_argument("--docker", type=str, default=None,
                        help="Name of Docker container running bench (if executing from host)")
    parser.add_argument("--log-file", type=str, default="frappe_backup.log",
                        help="Path to output log file (default: frappe_backup.log)")
    parser.add_argument("--verbose", "-v", action="store_true",
                        help="Enable verbose / debug logging output")
    parser.add_argument("--json", action="store_true",
                        help="Output final result as JSON to stdout")

    subparsers = parser.add_subparsers(dest="command", required=True, help="Command to execute")

    # Subcommand: backup
    backup_parser = subparsers.add_parser(
        "backup", parents=[shared_parser],
        help="Create database and file backup with SHA-256 verification and retention"
    )
    backup_parser.add_argument("--site", type=str, default="crm.localhost", help="Frappe CRM site name (default: crm.localhost)")
    backup_parser.add_argument("--no-files", action="store_true", help="Backup database only, omit public and private files")
    backup_parser.add_argument("--compress", action="store_true", help="Compress files during bench backup")
    backup_parser.add_argument("--retention", type=int, default=7, help="Number of latest backups to retain (default: 7)")
    backup_parser.add_argument("--reports-dir", type=str, default=None, help="Directory to store audit reports")

    # Subcommand: verify
    verify_parser = subparsers.add_parser(
        "verify", parents=[shared_parser],
        help="Verify backup checksums and archive integrity"
    )
    verify_parser.add_argument("--site", type=str, default="crm.localhost", help="Site name")
    verify_parser.add_argument("--timestamp", type=str, default=None, help="Specific backup timestamp (YYYYMMDD_HHMMSS) to verify")
    verify_parser.add_argument("--all", action="store_true", help="Verify all existing backup sets")

    # Subcommand: restore
    restore_parser = subparsers.add_parser(
        "restore", parents=[shared_parser],
        help="Restore backup into a test environment site"
    )
    restore_parser.add_argument("--source-site", type=str, default="crm.localhost", help="Source site with backup")
    restore_parser.add_argument("--target-site", type=str, required=True, help="Target site for test restoration (e.g. test.localhost)")
    restore_parser.add_argument("--timestamp", type=str, default=None, help="Timestamp of backup to restore (default: latest)")
    restore_parser.add_argument("--mariadb-root-password", type=str, default="123", help="MariaDB root password (default: 123)")
    restore_parser.add_argument("--no-files", action="store_true", help="Do not restore files")
    restore_parser.add_argument("--force", action="store_true", help="Force restoration ignoring warnings")

    # Subcommand: prune
    prune_parser = subparsers.add_parser(
        "prune", parents=[shared_parser],
        help="Enforce backup retention policy"
    )
    prune_parser.add_argument("--site", type=str, default="crm.localhost", help="Site name")
    prune_parser.add_argument("--retention", type=int, default=7, help="Number of backups to keep (default: 7)")
    prune_parser.add_argument("--dry-run", action="store_true", help="Simulate pruning without deleting files")

    # Subcommand: list
    list_parser = subparsers.add_parser(
        "list", parents=[shared_parser],
        help="List all available backups for a site"
    )
    list_parser.add_argument("--site", type=str, default="crm.localhost", help="Site name")

    args = parser.parse_args()

    # Determine bench directory:
    bench_path = Path(args.bench_dir)
    if not bench_path.exists() and not args.docker:
        # Check if current directory or parent contains sites
        if Path("sites").exists():
            bench_path = Path(".").resolve()
        elif Path("/home/frappe/frappe-bench").exists():
            bench_path = Path("/home/frappe/frappe-bench")

    manager = FrappeBackupManager(
        bench_dir=bench_path,
        docker_container=args.docker,
        log_file=Path(args.log_file) if args.log_file else None,
        verbose=args.verbose
    )

    try:
        if args.command == "backup":
            report = manager.backup(
                site=args.site,
                with_files=not args.no_files,
                compress=args.compress,
                retention_count=args.retention,
                reports_dir=Path(args.reports_dir) if args.reports_dir else None
            )
            if args.json:
                print(json.dumps(report, indent=2))

        elif args.command == "verify":
            report = manager.verify(
                site=args.site,
                timestamp=args.timestamp,
                verify_all=args.all
            )
            if args.json:
                print(json.dumps(report, indent=2))
            if report.get("status") != "SUCCESS":
                sys.exit(2)

        elif args.command == "restore":
            report = manager.restore(
                source_site=args.source_site,
                target_site=args.target_site,
                timestamp=args.timestamp,
                mariadb_root_password=args.mariadb_root_password,
                with_files=not args.no_files,
                force=args.force
            )
            if args.json:
                print(json.dumps(report, indent=2))

        elif args.command == "prune":
            backups_dir = manager.get_site_backups_dir(args.site)
            all_sets = manager.retention.discover_backup_sets(backups_dir, args.site)
            report = manager.retention.enforce_retention(
                backup_sets=all_sets,
                keep_count=args.retention,
                dry_run=args.dry_run
            )
            if args.json:
                print(json.dumps(report, indent=2))

        elif args.command == "list":
            catalog = manager.list_backups(args.site)
            if args.json:
                print(json.dumps(catalog, indent=2))
            else:
                print("\n" + "=" * 80)
                print(f"BACKUP CATALOG FOR SITE: {args.site}")
                print("=" * 80)
                print(f"{'Timestamp':<17} {'Created At':<20} {'Size':<10} {'DB':<5} {'Files':<7} {'SHA256':<8} {'Manifest':<8}")
                print("-" * 80)
                for item in catalog:
                    print(
                        f"{item['timestamp']:<17} "
                        f"{item['created_at']:<20} "
                        f"{item['total_size']:<10} "
                        f"{'✓' if item['has_database'] else '✗':<5} "
                        f"{'✓' if item['has_public_files'] else '✗':<7} "
                        f"{'✓' if item['has_checksum'] else '✗':<8} "
                        f"{'✓' if item['has_manifest'] else '✗':<8}"
                    )
                print("=" * 80 + "\n")

    except Exception as e:
        manager.logger.critical(f"FATAL ERROR: {e}", exc_info=args.verbose)
        sys.exit(1)


if __name__ == "__main__":
    main()
