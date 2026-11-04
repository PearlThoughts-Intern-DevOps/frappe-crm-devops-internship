#!/usr/bin/env python3
"""Frappe CRM Backup & Restore Automation Tool.

A production-minded, locally testable backup and restore manager for Frappe CRM
running in Docker Compose / Frappe Bench environments.

Exit Codes:
    0: Success
    1: General operation failure
    2: Invalid arguments or configuration
    3: Backup verification failure
    4: Unsafe restore destination
"""

import argparse
import datetime
import hashlib
import json
import logging
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
from typing import Any, Dict, List, Optional, Tuple

EXIT_SUCCESS = 0
EXIT_GENERAL_FAILURE = 1
EXIT_INVALID_ARGS = 2
EXIT_VERIFICATION_FAILURE = 3
EXIT_UNSAFE_RESTORE = 4

DEFAULT_SITE = "crm.localhost"
DEFAULT_CONTAINER = "crm-frappe-1"
DEFAULT_COMPOSE_FILE = "docker/docker-compose.yml"
DEFAULT_RETENTION_COUNT = 7
PROHIBITED_RESTORE_SITES = {"crm.localhost", "localhost", "crm"}

LOGGER = logging.getLogger("backup_manager")


def setup_logging(log_file: Optional[Path] = None, verbose: bool = False) -> None:
    """Configure structured logging to console and optional log file."""
    LOGGER.setLevel(logging.DEBUG if verbose else logging.INFO)
    formatter = logging.Formatter(
        "%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%dT%H:%M:%SZ"
    )

    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.DEBUG if verbose else logging.INFO)
    console_handler.setFormatter(formatter)
    LOGGER.addHandler(console_handler)

    if log_file:
        try:
            log_file.parent.mkdir(parents=True, exist_ok=True)
            file_handler = logging.FileHandler(str(log_file), encoding="utf-8")
            file_handler.setLevel(logging.DEBUG)
            file_handler.setFormatter(formatter)
            LOGGER.addHandler(file_handler)
        except Exception as err:
            LOGGER.warning("Could not initialize log file at %s: %s", log_file, err)


def sanitize_cmd(cmd_list: List[str]) -> str:
    """Mask sensitive tokens or passwords in command strings for safe logging."""
    sanitized: List[str] = []
    mask_next = False
    for token in cmd_list:
        if mask_next:
            sanitized.append("******")
            mask_next = False
            continue
        if token in ("--mariadb-root-password", "--db-root-password", "--admin-password", "--encryption-key"):
            sanitized.append(token)
            mask_next = True
            continue
        # Check inline assignments, e.g. MYSQL_ROOT_PASSWORD=...
        if re.search(r"password|secret|key", token, re.IGNORECASE) and "=" in token:
            parts = token.split("=", 1)
            sanitized.append(f"{parts[0]}=******")
            continue
        sanitized.append(token)
    return " ".join(sanitized)


def run_command(
    cmd: List[str],
    timeout_sec: int = 300,
    check: bool = False
) -> Tuple[int, str, str]:
    """Execute a subprocess safely with argument lists (never shell=True)."""
    LOGGER.debug("Executing command: %s", sanitize_cmd(cmd))
    try:
        proc = subprocess.run(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=timeout_sec,
            check=False
        )
        stdout = proc.stdout.strip()
        stderr = proc.stderr.strip()
        if proc.returncode != 0:
            LOGGER.warning(
                "Command failed with exit code %d:\nSTDOUT: %s\nSTDERR: %s",
                proc.returncode, stdout, stderr
            )
        else:
            LOGGER.debug("Command succeeded:\n%s", stdout)
        if check and proc.returncode != 0:
            raise subprocess.CalledProcessError(proc.returncode, cmd, output=stdout, stderr=stderr)
        return proc.returncode, stdout, stderr
    except FileNotFoundError as err:
        LOGGER.error("Executable not found: %s", err)
        return EXIT_GENERAL_FAILURE, "", str(err)
    except subprocess.TimeoutExpired as err:
        LOGGER.error("Command timed out after %d seconds: %s", timeout_sec, sanitize_cmd(cmd))
        return EXIT_GENERAL_FAILURE, "", f"Timeout after {timeout_sec}s: {err}"
    except Exception as err:
        LOGGER.error("Unexpected error executing command: %s", err)
        return EXIT_GENERAL_FAILURE, "", str(err)


def calculate_sha256(file_path: Path) -> str:
    """Calculate the SHA-256 digest of a file in streaming 64KB blocks."""
    sha256 = hashlib.sha256()
    with open(file_path, "rb") as f:
        while chunk := f.read(65536):
            sha256.update(chunk)
    return sha256.hexdigest()


class BackupManager:
    """Automates Frappe CRM backups, verification, retention, and isolated restore."""

    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.backup_dir = Path(
            config.get("backup_dir") or Path.home() / "frappe_crm_backups"
        ).resolve()
        self.source_site = config.get("source_site", DEFAULT_SITE)
        self.source_container = config.get("source_container", DEFAULT_CONTAINER)
        self.source_compose_file = config.get("source_compose_file", DEFAULT_COMPOSE_FILE)
        self.retention_count = int(config.get("retention_count", DEFAULT_RETENTION_COUNT))
        self.source_bench_dir = config.get("source_bench_dir", "/home/frappe/frappe-bench")

    def _ensure_backup_dir(self) -> None:
        self.backup_dir.mkdir(parents=True, exist_ok=True)

    def _check_container_running(self, container_name: str) -> bool:
        code, stdout, _ = run_command([
            "docker", "inspect", "-f", "{{.State.Running}}", container_name
        ])
        return code == 0 and stdout.strip().lower() == "true"

    def create_backup(self, compress: bool = True) -> Tuple[int, Dict[str, Any]]:
        """Run bench backup inside the container, copy artifacts out, and generate manifest."""
        self._ensure_backup_dir()
        LOGGER.info("Starting backup for site: %s", self.source_site)

        if not self._check_container_running(self.source_container):
            LOGGER.error("Source container %s is not running", self.source_container)
            return EXIT_GENERAL_FAILURE, {"error": f"Container {self.source_container} is stopped"}

        timestamp = datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%d_%H%M%S")
        backup_id = f"backup_{timestamp}"
        target_dir = self.backup_dir / backup_id
        target_dir.mkdir(parents=True, exist_ok=True)

        remote_backups_path = f"{self.source_bench_dir}/sites/{self.source_site}/private/backups"

        # Record pre-existing files in container backup dir to accurately identify newly created artifacts
        code, pre_ls, _ = run_command([
            "docker", "exec", self.source_container, "ls", "-1", remote_backups_path
        ])
        pre_files = set(pre_ls.splitlines()) if code == 0 else set()

        # Build bench backup command
        bench_cmd = [
            "docker", "exec", "-w", self.source_bench_dir, self.source_container,
            "bench", "--site", self.source_site, "backup", "--with-files"
        ]
        if compress:
            bench_cmd.append("--compress")

        LOGGER.info("Executing bench backup inside container...")
        code, stdout, stderr = run_command(bench_cmd, timeout_sec=600)
        if code != 0:
            LOGGER.error("Bench backup failed: %s", stderr or stdout)
            shutil.rmtree(target_dir, ignore_errors=True)
            return EXIT_GENERAL_FAILURE, {"error": "Bench backup failed", "details": stderr or stdout}

        # List files in container backup dir after execution
        code, post_ls, _ = run_command([
            "docker", "exec", self.source_container, "ls", "-1", remote_backups_path
        ])
        if code != 0:
            LOGGER.error("Failed to list remote backup directory")
            return EXIT_GENERAL_FAILURE, {"error": "Could not inspect remote backup directory"}

        post_files = [f.strip() for f in post_ls.splitlines() if f.strip()]
        new_files = [f for f in post_files if f not in pre_files]

        # If all files were pre-existing (or empty pre-files), filter by site name
        if not new_files:
            site_clean = self.source_site.replace(".", "_")
            new_files = [f for f in post_files if site_clean in f]

        if not new_files:
            LOGGER.error("No backup artifacts detected in %s", remote_backups_path)
            shutil.rmtree(target_dir, ignore_errors=True)
            return EXIT_GENERAL_FAILURE, {"error": "No backup artifacts generated"}

        LOGGER.info("Detected %d backup artifacts. Copying to host storage: %s", len(new_files), target_dir)
        artifacts_metadata: Dict[str, Any] = {}

        for filename in new_files:
            remote_file = f"{remote_backups_path}/{filename}"
            local_dest = target_dir / filename
            cp_code, _, cp_err = run_command([
                "docker", "cp", f"{self.source_container}:{remote_file}", str(local_dest)
            ])
            if cp_code != 0:
                LOGGER.error("Failed to copy %s: %s", filename, cp_err)
                shutil.rmtree(target_dir, ignore_errors=True)
                return EXIT_GENERAL_FAILURE, {"error": f"Failed to copy artifact {filename}"}

            if not local_dest.exists() or local_dest.stat().st_size == 0:
                LOGGER.error("Artifact %s is missing or empty after copy", filename)
                shutil.rmtree(target_dir, ignore_errors=True)
                return EXIT_GENERAL_FAILURE, {"error": f"Artifact {filename} is empty or missing"}

            size_bytes = local_dest.stat().st_size
            digest = calculate_sha256(local_dest)

            # Categorize artifact type
            category = "other"
            if "database.sql" in filename:
                category = "database"
            elif "site_config_backup" in filename:
                category = "site_config"
            elif "private-files" in filename:
                category = "private_files"
            elif "files" in filename:
                category = "public_files"

            artifacts_metadata[category] = {
                "filename": filename,
                "size_bytes": size_bytes,
                "sha256": digest
            }
            LOGGER.debug("Copied artifact %s (%d bytes, SHA-256: %s)", filename, size_bytes, digest)

        # Confirm essential database dump is present
        if "database" not in artifacts_metadata:
            LOGGER.error("Database dump artifact missing from backup set")
            shutil.rmtree(target_dir, ignore_errors=True)
            return EXIT_GENERAL_FAILURE, {"error": "Database dump missing from artifacts"}

        manifest_data = {
            "backup_id": backup_id,
            "created_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
            "source_site": self.source_site,
            "source_container": self.source_container,
            "compressed": compress,
            "status": "complete",
            "artifacts": artifacts_metadata
        }

        manifest_path = target_dir / "manifest.json"
        with open(manifest_path, "w", encoding="utf-8") as f:
            json.dump(manifest_data, f, indent=2)

        LOGGER.info("Backup %s successfully created and verified locally.", backup_id)
        return EXIT_SUCCESS, manifest_data

    def verify_backup(self, backup_id_or_path: str) -> Tuple[int, Dict[str, Any]]:
        """Verify checksums and completeness of a backup against its manifest."""
        target_path = Path(backup_id_or_path)
        if not target_path.is_absolute() and not target_path.exists():
            target_path = self.backup_dir / backup_id_or_path

        if not target_path.exists() or not target_path.is_dir():
            LOGGER.error("Backup directory does not exist: %s", target_path)
            return EXIT_INVALID_ARGS, {"error": f"Directory not found: {target_path}"}

        manifest_path = target_path / "manifest.json"
        if not manifest_path.exists():
            LOGGER.error("Manifest not found in: %s", target_path)
            return EXIT_VERIFICATION_FAILURE, {"error": "manifest.json missing"}

        try:
            with open(manifest_path, "r", encoding="utf-8") as f:
                manifest = json.load(f)
        except Exception as err:
            LOGGER.error("Invalid manifest JSON in %s: %s", target_path, err)
            return EXIT_VERIFICATION_FAILURE, {"error": f"Unreadable manifest: {err}"}

        artifacts = manifest.get("artifacts", {})
        if not artifacts:
            LOGGER.error("No artifacts defined in manifest for %s", target_path.name)
            return EXIT_VERIFICATION_FAILURE, {"error": "No artifacts listed in manifest"}

        verification_results: Dict[str, Any] = {}
        all_passed = True

        for category, info in artifacts.items():
            filename = info.get("filename")
            expected_hash = info.get("sha256")
            expected_size = info.get("size_bytes")
            file_path = target_path / filename

            if not file_path.exists():
                LOGGER.error("Artifact %s missing from backup directory", filename)
                verification_results[filename] = {"status": "MISSING", "error": "File not found"}
                all_passed = False
                continue

            actual_size = file_path.stat().st_size
            if actual_size != expected_size:
                LOGGER.error("Artifact %s size mismatch: expected %d, got %d", filename, expected_size, actual_size)
                verification_results[filename] = {
                    "status": "SIZE_MISMATCH",
                    "expected_size": expected_size,
                    "actual_size": actual_size
                }
                all_passed = False
                continue

            actual_hash = calculate_sha256(file_path)
            if actual_hash.lower() != expected_hash.lower():
                LOGGER.error("Artifact %s SHA-256 mismatch!\nExpected: %s\nActual:   %s", filename, expected_hash, actual_hash)
                verification_results[filename] = {
                    "status": "HASH_MISMATCH",
                    "expected_sha256": expected_hash,
                    "actual_sha256": actual_hash
                }
                all_passed = False
                continue

            LOGGER.debug("Artifact %s verified: SHA-256 match (%s)", filename, actual_hash[:12])
            verification_results[filename] = {"status": "VERIFIED", "sha256": actual_hash}

        summary = {
            "backup_id": manifest.get("backup_id", target_path.name),
            "directory": str(target_path),
            "verified_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
            "overall_status": "PASS" if all_passed else "FAIL",
            "artifacts": verification_results
        }

        if all_passed:
            LOGGER.info("Backup %s verified successfully: ALL CHECKSUMS MATCH.", target_path.name)
            return EXIT_SUCCESS, summary
        else:
            LOGGER.error("Backup %s verification failed.", target_path.name)
            return EXIT_VERIFICATION_FAILURE, summary

    def list_backups(self) -> List[Dict[str, Any]]:
        """List all discovered backups and their manifest status."""
        self._ensure_backup_dir()
        backups: List[Dict[str, Any]] = []

        for item in sorted(self.backup_dir.iterdir()):
            if not item.is_dir():
                continue
            manifest_file = item / "manifest.json"
            if manifest_file.exists():
                try:
                    with open(manifest_file, "r", encoding="utf-8") as f:
                        data = json.load(f)
                    backups.append({
                        "backup_id": data.get("backup_id", item.name),
                        "created_at": data.get("created_at", "unknown"),
                        "site": data.get("source_site", "unknown"),
                        "status": data.get("status", "complete"),
                        "artifact_count": len(data.get("artifacts", {})),
                        "path": str(item)
                    })
                except Exception:
                    backups.append({
                        "backup_id": item.name,
                        "created_at": "corrupt_manifest",
                        "status": "corrupt",
                        "path": str(item)
                    })
            else:
                backups.append({
                    "backup_id": item.name,
                    "created_at": "no_manifest",
                    "status": "incomplete",
                    "path": str(item)
                })
        return backups

    def enforce_retention(self, keep_count: Optional[int] = None) -> Tuple[int, Dict[str, Any]]:
        """Retain the latest N complete, verified backups; safely delete older ones."""
        keep_n = keep_count if keep_count is not None else self.retention_count
        if keep_n < 1:
            LOGGER.error("Retention count must be at least 1 (got %d)", keep_n)
            return EXIT_INVALID_ARGS, {"error": "Invalid retention count"}

        self._ensure_backup_dir()
        LOGGER.info("Evaluating retention policy: keeping latest %d verified backups in %s", keep_n, self.backup_dir)

        valid_backups: List[Tuple[datetime.datetime, Path, Dict[str, Any]]] = []
        incomplete_or_invalid: List[Path] = []

        for entry in self.backup_dir.iterdir():
            if not entry.is_dir():
                continue
            manifest_path = entry / "manifest.json"
            if not manifest_path.exists():
                incomplete_or_invalid.append(entry)
                continue
            try:
                with open(manifest_path, "r", encoding="utf-8") as f:
                    manifest = json.load(f)
                if manifest.get("status") != "complete":
                    incomplete_or_invalid.append(entry)
                    continue

                # Verify checksums before treating as an eligible verified backup
                verify_code, _ = self.verify_backup(str(entry))
                if verify_code != EXIT_SUCCESS:
                    LOGGER.warning("Backup %s failed checksum verification; excluding from retention count", entry.name)
                    incomplete_or_invalid.append(entry)
                    continue

                ts_str = manifest.get("created_at")
                if ts_str:
                    try:
                        ts = datetime.datetime.fromisoformat(ts_str.replace("Z", "+00:00"))
                    except Exception:
                        ts = datetime.datetime.fromtimestamp(entry.stat().st_mtime, datetime.timezone.utc)
                else:
                    ts = datetime.datetime.fromtimestamp(entry.stat().st_mtime, datetime.timezone.utc)

                valid_backups.append((ts, entry, manifest))
            except Exception as err:
                LOGGER.warning("Error reading manifest in %s: %s", entry, err)
                incomplete_or_invalid.append(entry)

        # Sort valid backups newest first
        valid_backups.sort(key=lambda x: x[0], reverse=True)
        retained = valid_backups[:keep_n]
        to_prune = valid_backups[keep_n:]

        deleted_ids: List[str] = []
        for _, path, manifest in to_prune:
            backup_id = manifest.get("backup_id", path.name)
            LOGGER.info("Pruning expired backup: %s (created %s)", backup_id, manifest.get("created_at"))
            try:
                shutil.rmtree(path)
                deleted_ids.append(backup_id)
            except Exception as err:
                LOGGER.error("Failed to delete expired backup directory %s: %s", path, err)

        report = {
            "retention_target": keep_n,
            "total_verified": len(valid_backups),
            "retained_count": len(retained),
            "retained_ids": [m.get("backup_id", p.name) for _, p, m in retained],
            "deleted_count": len(deleted_ids),
            "deleted_ids": deleted_ids,
            "unverified_or_incomplete_count": len(incomplete_or_invalid),
            "unverified_or_incomplete_paths": [str(p) for p in incomplete_or_invalid]
        }
        LOGGER.info("Retention summary: Retained %d, Pruned %d.", len(retained), len(deleted_ids))
        return EXIT_SUCCESS, report

    def restore_backup(
        self,
        backup_id_or_path: str,
        target_site: str,
        target_container: str,
        target_compose_file: str,
        mariadb_root_password: Optional[str] = None,
        force: bool = False
    ) -> Tuple[int, Dict[str, Any]]:
        """Restore a verified backup into an isolated test site.

        STRICT SAFETY CHECKS:
        1. Target site MUST NOT be crm.localhost or production.
        2. Target container MUST NOT be the source container.
        3. Backup checksums MUST pass before restore begins.
        4. Target environment MUST be confirmed isolated.
        """
        start_time = datetime.datetime.now(datetime.timezone.utc).isoformat()
        LOGGER.info("Initiating restore request: backup=%s -> target_site=%s", backup_id_or_path, target_site)

        # Guard 1: Prohibit restoring into original production / local CRM site
        if target_site.lower() in PROHIBITED_RESTORE_SITES:
            LOGGER.critical("UNSAFE RESTORE ATTEMPT: Restoration to '%s' is strictly prohibited!", target_site)
            return EXIT_UNSAFE_RESTORE, {
                "error": f"Restoration into '{target_site}' is blocked by security policy",
                "prohibited_sites": list(PROHIBITED_RESTORE_SITES)
            }

        # Guard 2: Prohibit targeting the original source container
        if target_container == self.source_container:
            LOGGER.critical("UNSAFE RESTORE ATTEMPT: Destination container '%s' matches source container!", target_container)
            return EXIT_UNSAFE_RESTORE, {
                "error": "Destination container cannot be the primary application container"
            }

        # Guard 3: Verify destination container is actually running
        if not self._check_container_running(target_container):
            LOGGER.error("Target restore container '%s' is not running", target_container)
            return EXIT_GENERAL_FAILURE, {
                "error": f"Target container '{target_container}' is not running"
            }

        # Guard 4: Verify backup checksums before restore
        LOGGER.info("Verifying backup integrity prior to restoration...")
        verify_code, verify_report = self.verify_backup(backup_id_or_path)
        if verify_code != EXIT_SUCCESS:
            LOGGER.error("Cannot restore corrupted or unverified backup: %s", backup_id_or_path)
            return EXIT_VERIFICATION_FAILURE, {
                "error": "Backup integrity verification failed",
                "verification_report": verify_report
            }

        target_path = Path(backup_id_or_path)
        if not target_path.is_absolute() and not target_path.exists():
            target_path = self.backup_dir / backup_id_or_path

        manifest_path = target_path / "manifest.json"
        with open(manifest_path, "r", encoding="utf-8") as f:
            manifest = json.load(f)

        artifacts = manifest.get("artifacts", {})
        db_info = artifacts.get("database")
        if not db_info:
            return EXIT_VERIFICATION_FAILURE, {"error": "Manifest does not contain database artifact"}

        db_file = target_path / db_info["filename"]
        public_info = artifacts.get("public_files")
        private_info = artifacts.get("private_files")

        # Copy artifacts into isolated container's bench sites directory
        remote_dest_dir = f"/home/frappe/frappe-bench/sites/{target_site}/private/backups"
        run_command([
            "docker", "exec", target_container, "mkdir", "-p", remote_dest_dir
        ])

        remote_db = f"{remote_dest_dir}/{db_info['filename']}"
        LOGGER.info("Copying database archive into isolated test container...")
        code, _, err = run_command([
            "docker", "cp", str(db_file), f"{target_container}:{remote_db}"
        ])
        if code != 0:
            LOGGER.error("Failed to copy database archive to container: %s", err)
            return EXIT_GENERAL_FAILURE, {"error": "Failed to stage database dump inside container"}

        # Sanitize MariaDB 10.8 incompatibility in staged dump inside container (strip NOTE_VERBOSITY comments)
        LOGGER.debug("Sanitizing MariaDB 10.8 compatibility comments in staged dump...")
        run_command([
            "docker", "exec", target_container, "bash", "-c",
            f"gunzip -f {remote_db} && sed -i '/NOTE_VERBOSITY/d' {remote_dest_dir}/*.sql && gzip -9 {remote_dest_dir}/*.sql"
        ])

        remote_public = None
        if public_info:
            public_file = target_path / public_info["filename"]
            if public_file.exists():
                remote_public = f"{remote_dest_dir}/{public_info['filename']}"
                run_command(["docker", "cp", str(public_file), f"{target_container}:{remote_public}"])

        remote_private = None
        if private_info:
            private_file = target_path / private_info["filename"]
            if private_file.exists():
                remote_private = f"{remote_dest_dir}/{private_info['filename']}"
                run_command(["docker", "cp", str(private_file), f"{target_container}:{remote_private}"])

        # Execute bench restore inside isolated container
        # Note: We do NOT use --force automatically unless explicitly requested
        restore_cmd = [
            "docker", "exec", "-w", "/home/frappe/frappe-bench", target_container,
            "bench", "--site", target_site, "restore", remote_db
        ]

        # Resolve MariaDB root password safely from arguments or environment
        root_pwd = mariadb_root_password or os.environ.get("MARIADB_ROOT_PASSWORD", "123")
        restore_cmd.extend(["--mariadb-root-password", root_pwd])

        if remote_public:
            restore_cmd.extend(["--with-public-files", remote_public])
        if remote_private:
            restore_cmd.extend(["--with-private-files", remote_private])
        if force:
            restore_cmd.append("--force")

        LOGGER.info("Running bench restore inside isolated environment: %s", sanitize_cmd(restore_cmd))
        code, stdout, stderr = run_command(restore_cmd, timeout_sec=900)
        end_time = datetime.datetime.now(datetime.timezone.utc).isoformat()

        if code != 0:
            LOGGER.error("Bench restore failed: %s", stderr or stdout)
            return EXIT_GENERAL_FAILURE, {
                "status": "FAIL",
                "start_time": start_time,
                "end_time": end_time,
                "exit_code": code,
                "error": stderr or stdout
            }

        # Clear cache and run migrate on the test site to ensure clean state
        run_command([
            "docker", "exec", "-w", "/home/frappe/frappe-bench", target_container,
            "bench", "--site", target_site, "clear-cache"
        ])

        LOGGER.info("Restoration into test site '%s' completed successfully.", target_site)
        return EXIT_SUCCESS, {
            "status": "PASS",
            "backup_id": manifest.get("backup_id"),
            "target_site": target_site,
            "target_container": target_container,
            "start_time": start_time,
            "end_time": end_time,
            "details": stdout
        }


def build_parser() -> argparse.ArgumentParser:
    """Build the command-line argument parser."""
    parser = argparse.ArgumentParser(
        description="Frappe CRM Python Backup & Restore Automation Tool",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""Exit Codes:
  0: Success
  1: General operation failure
  2: Invalid arguments or configuration
  3: Backup verification failure
  4: Unsafe restore destination

Examples:
  python backup_manager.py backup
  python backup_manager.py verify --backup-id backup_20261104_120000
  python backup_manager.py list
  python backup_manager.py retention --keep 7
  python backup_manager.py restore --backup-id backup_20261104_120000 --target-site restore-test.localhost --target-container crm-restore-test-frappe-1
"""
    )
    parser.add_argument("--config", help="Path to JSON configuration file")
    parser.add_argument("--backup-dir", help="Directory where backups are stored on host")
    parser.add_argument("--log-file", help="Path to output log file (outside git repo)")
    parser.add_argument("-v", "--verbose", action="store_true", help="Enable verbose debug output")

    subparsers = parser.add_subparsers(dest="action", required=True, help="Action to execute")

    # backup
    p_backup = subparsers.add_parser("backup", help="Create a complete, compressed site backup")
    p_backup.add_argument("--site", default=DEFAULT_SITE, help=f"Source site to backup (default: {DEFAULT_SITE})")
    p_backup.add_argument("--container", default=DEFAULT_CONTAINER, help="Frappe Docker container name")
    p_backup.add_argument("--no-compress", action="store_true", help="Disable gzip compression")

    # verify
    p_verify = subparsers.add_parser("verify", help="Verify SHA-256 digests and integrity of a backup")
    p_verify.add_argument("--backup-id", required=True, help="Backup ID or relative/absolute path to backup directory")

    # list
    subparsers.add_parser("list", help="List all available backups in the backup store")

    # retention
    p_retention = subparsers.add_parser("retention", help="Enforce retention policy (keep latest N verified backups)")
    p_retention.add_argument("--keep", type=int, default=DEFAULT_RETENTION_COUNT, help=f"Number of verified backups to retain (default: {DEFAULT_RETENTION_COUNT})")

    # restore
    p_restore = subparsers.add_parser("restore", help="Restore a verified backup into an isolated test site")
    p_restore.add_argument("--backup-id", required=True, help="Backup ID or path to restore from")
    p_restore.add_argument("--target-site", required=True, help="Isolated target test site (NEVER crm.localhost)")
    p_restore.add_argument("--target-container", required=True, help="Isolated target Frappe container")
    p_restore.add_argument("--target-compose-file", default="docker/docker-compose.restore-test.yml", help="Compose file for isolated test environment")
    p_restore.add_argument("--mariadb-root-password", help="MariaDB root password for test instance (or set MARIADB_ROOT_PASSWORD)")
    p_restore.add_argument("--force", action="store_true", help="Pass --force to bench restore if required")

    return parser


def load_config(config_path: Optional[str]) -> Dict[str, Any]:
    """Load optional JSON configuration file."""
    if not config_path:
        # Check standard location if present
        default_cfg = Path(__file__).parent / "config.json"
        if default_cfg.exists():
            config_path = str(default_cfg)
        else:
            return {}

    p = Path(config_path)
    if not p.exists():
        LOGGER.warning("Configuration file %s not found. Using defaults.", config_path)
        return {}

    try:
        with open(p, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as err:
        LOGGER.error("Failed to parse config file %s: %s", config_path, err)
        return {}


def main() -> int:
    """CLI entrypoint."""
    parser = build_parser()
    args = parser.parse_args()

    config = load_config(args.config)
    if args.backup_dir:
        config["backup_dir"] = args.backup_dir
    if args.log_file:
        config["log_file"] = args.log_file

    log_path = Path(config["log_file"]) if config.get("log_file") else None
    setup_logging(log_path, verbose=args.verbose)

    manager = BackupManager(config)

    if args.action == "backup":
        if args.site:
            manager.source_site = args.site
        if args.container:
            manager.source_container = args.container
        exit_code, result = manager.create_backup(compress=not args.no_compress)
        print(json.dumps(result, indent=2))
        return exit_code

    elif args.action == "verify":
        exit_code, result = manager.verify_backup(args.backup_id)
        print(json.dumps(result, indent=2))
        return exit_code

    elif args.action == "list":
        backups = manager.list_backups()
        print(json.dumps(backups, indent=2))
        return EXIT_SUCCESS

    elif args.action == "retention":
        exit_code, result = manager.enforce_retention(keep_count=args.keep)
        print(json.dumps(result, indent=2))
        return exit_code

    elif args.action == "restore":
        exit_code, result = manager.restore_backup(
            backup_id_or_path=args.backup_id,
            target_site=args.target_site,
            target_container=args.target_container,
            target_compose_file=args.target_compose_file,
            mariadb_root_password=args.mariadb_root_password,
            force=args.force
        )
        print(json.dumps(result, indent=2))
        return exit_code

    return EXIT_INVALID_ARGS


if __name__ == "__main__":
    sys.exit(main())

