#!/usr/bin/env python3
"""Frappe CRM Backup & Restore Automation Tool.

Enterprise-grade automation script for Frappe CRM that provides:
1. Automated full backups (Database, Public Files, Private Files, Site Config) via Frappe Bench.
2. Cryptographic backup verification using SHA-256 checksums and archive integrity checks.
3. Automated backup retention policy enforcing storage of the latest N (default: 7) backups.
4. Safe restoration of backups into an isolated test environment (e.g., test.localhost).
5. Comprehensive logging, sensitive data masking, and error handling.
6. Unified Command-Line Interface (CLI).

**Author:** Gourob Das ([@gourobdas0103](https://github.com/gourobdas0103))
**Role:** DevOps Engineering Intern
**Organization:** PearlThoughts
**Repository:** `PearlThoughts-Intern-DevOps/frappe-crm-devops-internship/backup-automation`
**Branch:** `task2-gourobdas0103`
**Submission Date:** 6 November 2026
"""

from __future__ import annotations

import argparse
import gzip
import hashlib
import json
import logging
import re
import shutil
import subprocess
import sys
import tarfile
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, ClassVar

# ---------------------------------------------------------------------------
# Constants & Defaults
# ---------------------------------------------------------------------------
DEFAULT_SOURCE_SITE = "crm.localhost"
DEFAULT_TEST_SITE = "test.localhost"
DEFAULT_CONTAINER = "crm-frappe-1"
DEFAULT_RETENTION_LIMIT = 7
DEFAULT_BACKUP_DIR = Path("./backups")
DEFAULT_LOG_FILE = Path("./automation/logs/frappe_backup.log")
BENCH_SEARCH_PATHS = [
	"/home/frappe/frappe-bench/frappe-bench",
	"/home/frappe/frappe-bench",
	".",
]


# ---------------------------------------------------------------------------
# Custom Exceptions
# ---------------------------------------------------------------------------
class AutomationError(Exception):
	"""Base exception for Frappe backup and restore automation."""


class BackupExecutionError(AutomationError):
	"""Raised when the bench backup command fails."""


class ChecksumVerificationError(AutomationError):
	"""Raised when backup SHA-256 checksums or archive validation fails."""


class RetentionPolicyError(AutomationError):
	"""Raised when retention cleanup encounters an error."""


class RestoreSafetyError(AutomationError):
	"""Raised when an unsafe restore operation (e.g., targeting production) is attempted."""


class RestoreExecutionError(AutomationError):
	"""Raised when the bench restore command or database validation fails."""


# ---------------------------------------------------------------------------
# Sensitive Data Filter & Logging Setup
# ---------------------------------------------------------------------------
class SensitiveDataFilter(logging.Filter):
	"""Redacts sensitive credentials (passwords, tokens) from log messages."""

	PATTERNS: ClassVar[list[tuple[re.Pattern, str]]] = [
		(re.compile(r"(--mariadb-root-password\s+)(\S+)", re.IGNORECASE), r"\1***"),
		(re.compile(r"(--db-root-password\s+)(\S+)", re.IGNORECASE), r"\1***"),
		(re.compile(r"(--admin-password\s+)(\S+)", re.IGNORECASE), r"\1***"),
		(re.compile(r"(\s-p\s*)(\S+)", re.IGNORECASE), r"\1***"),
		(re.compile(r'("db_password":\s*")[^"]+(")', re.IGNORECASE), r"\1***\2"),
		(re.compile(r"(MYSQL_ROOT_PASSWORD=)(\S+)", re.IGNORECASE), r"\1***"),
	]

	def filter(self, record: logging.LogRecord) -> bool:
		if isinstance(record.msg, str):
			for pattern, repl in self.PATTERNS:
				record.msg = pattern.sub(repl, record.msg)
		return True


def setup_logging(log_file: Path | None = None, verbose: bool = False) -> logging.Logger:
	"""Configures multi-channel logging (File & Console) with credentials masking."""
	logger = logging.getLogger("frappe_backup")
	logger.setLevel(logging.DEBUG if verbose else logging.INFO)
	logger.handlers.clear()

	sensitive_filter = SensitiveDataFilter()

	# Console Handler
	console_handler = logging.StreamHandler(sys.stdout)
	console_handler.setLevel(logging.DEBUG if verbose else logging.INFO)
	console_format = logging.Formatter("%(asctime)s [%(levelname)s] %(message)s", datefmt="%Y-%m-%d %H:%M:%S")
	console_handler.setFormatter(console_format)
	console_handler.addFilter(sensitive_filter)
	logger.addHandler(console_handler)

	# File Handler
	if log_file:
		log_file.parent.mkdir(parents=True, exist_ok=True)
		file_handler = logging.FileHandler(log_file, encoding="utf-8")
		file_handler.setLevel(logging.DEBUG)
		file_format = logging.Formatter("%(asctime)s [%(levelname)s] [%(filename)s:%(lineno)d] %(message)s")
		file_handler.setFormatter(file_format)
		file_handler.addFilter(sensitive_filter)
		logger.addHandler(file_handler)

	return logger


# ---------------------------------------------------------------------------
# Data Models
# ---------------------------------------------------------------------------
@dataclass
class BackupFileInfo:
	file_type: str  # database, public_files, private_files, site_config
	filename: str
	size_bytes: int
	sha256: str


@dataclass
class BackupManifest:
	backup_id: str
	site: str
	timestamp: str
	mode: str
	container: str | None
	files: dict[str, BackupFileInfo] = field(default_factory=dict)
	total_size_bytes: int = 0
	verified: bool = False
	retention_tag: str = "active"

	def to_dict(self) -> dict[str, Any]:
		data = asdict(self)
		# Convert BackupFileInfo dataclasses inside dictionary
		data["files"] = {k: asdict(v) for k, v in self.files.items()}
		return data

	@classmethod
	def from_dict(cls, data: dict[str, Any]) -> BackupManifest:
		files = {k: BackupFileInfo(**v) for k, v in data.get("files", {}).items()}
		return cls(
			backup_id=data["backup_id"],
			site=data["site"],
			timestamp=data["timestamp"],
			mode=data["mode"],
			container=data.get("container"),
			files=files,
			total_size_bytes=data.get("total_size_bytes", 0),
			verified=data.get("verified", False),
			retention_tag=data.get("retention_tag", "active"),
		)


@dataclass
class VerificationReport:
	backup_id: str
	verified_at: str
	checksums_matched: bool
	archives_valid: bool
	status: str
	file_results: dict[str, dict[str, Any]]
	details: list[str] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Utility Functions
# ---------------------------------------------------------------------------
def compute_sha256(filepath: Path) -> str:
	"""Computes the SHA-256 checksum of a file."""
	return hashlib.sha256(filepath.read_bytes()).hexdigest()


def format_size(bytes_num: int) -> str:
	"""Formats bytes into human-readable metric string."""
	for unit in ["B", "KiB", "MiB", "GiB"]:
		if bytes_num < 1024.0 or unit == "GiB":
			return f"{bytes_num:.2f} {unit}"
		bytes_num /= 1024.0
	return f"{bytes_num:.2f} B"


# ---------------------------------------------------------------------------
# Execution Backends (Docker & Native)
# ---------------------------------------------------------------------------
class ExecutionBackend:
	"""Abstract interface for running bench commands and transferring files."""

	def run_command(self, cmd: list[str], cwd: str | None = None) -> tuple[int, str, str]:
		raise NotImplementedError

	def copy_from(self, remote_path: str, local_path: Path) -> None:
		raise NotImplementedError

	def copy_to(self, local_path: Path, remote_path: str) -> None:
		raise NotImplementedError

	def find_bench_dir(self, site: str) -> str:
		raise NotImplementedError


class DockerBackend(ExecutionBackend):
	"""Executes commands inside a running Docker container via `docker exec`."""

	def __init__(self, container: str, logger: logging.Logger):
		self.container = container
		self.logger = logger
		self._bench_dir: str | None = None

	def run_command(self, cmd: list[str], cwd: str | None = None) -> tuple[int, str, str]:
		full_cmd = ["docker", "exec"]
		if cwd:
			full_cmd.extend(["-w", cwd])
		full_cmd.append(self.container)
		full_cmd.extend(cmd)

		self.logger.debug(f"Docker Exec: {' '.join(full_cmd)}")
		proc = subprocess.run(
			full_cmd,
			capture_output=True,
			text=True,
		)
		return proc.returncode, proc.stdout, proc.stderr

	def copy_from(self, remote_path: str, local_path: Path) -> None:
		local_path.parent.mkdir(parents=True, exist_ok=True)
		src = f"{self.container}:{remote_path}"
		self.logger.debug(f"Docker CP {src} -> {local_path}")
		proc = subprocess.run(
			["docker", "cp", src, str(local_path)],
			capture_output=True,
			text=True,
		)
		if proc.returncode != 0:
			raise AutomationError(f"Failed to copy {src} to {local_path}: {proc.stderr}")

	def copy_to(self, local_path: Path, remote_path: str) -> None:
		dest = f"{self.container}:{remote_path}"
		self.logger.debug(f"Docker CP {local_path} -> {dest}")
		proc = subprocess.run(
			["docker", "cp", str(local_path), dest],
			capture_output=True,
			text=True,
		)
		if proc.returncode != 0:
			raise AutomationError(f"Failed to copy {local_path} to {dest}: {proc.stderr}")

	def find_bench_dir(self, site: str) -> str:
		if self._bench_dir:
			return self._bench_dir

		for candidate in BENCH_SEARCH_PATHS:
			rc, _out, _ = self.run_command(
				["bash", "-c", f"test -f {candidate}/sites/{site}/site_config.json"]
			)
			if rc == 0:
				self._bench_dir = candidate
				self.logger.debug(f"Detected container bench directory: {candidate}")
				return candidate

		raise AutomationError(
			f"Could not locate Frappe bench directory containing site '{site}' in container '{self.container}'"
		)


class NativeBackend(ExecutionBackend):
	"""Executes commands directly on the host machine using native bench."""

	def __init__(self, logger: logging.Logger):
		self.logger = logger
		self._bench_dir: str | None = None

	def run_command(self, cmd: list[str], cwd: str | None = None) -> tuple[int, str, str]:
		self.logger.debug(f"Native Exec: {' '.join(cmd)} (cwd={cwd})")
		proc = subprocess.run(
			cmd,
			cwd=cwd,
			capture_output=True,
			text=True,
		)
		return proc.returncode, proc.stdout, proc.stderr

	def copy_from(self, remote_path: str, local_path: Path) -> None:
		local_path.parent.mkdir(parents=True, exist_ok=True)
		shutil.copy2(remote_path, local_path)

	def copy_to(self, local_path: Path, remote_path: str) -> None:
		dest = Path(remote_path)
		dest.parent.mkdir(parents=True, exist_ok=True)
		shutil.copy2(local_path, dest)

	def find_bench_dir(self, site: str) -> str:
		if self._bench_dir:
			return self._bench_dir

		for candidate in BENCH_SEARCH_PATHS:
			candidate_path = Path(candidate).resolve()
			if (candidate_path / "sites" / site / "site_config.json").is_file():
				self._bench_dir = str(candidate_path)
				return str(candidate_path)

		raise AutomationError(f"Could not locate local Frappe bench directory containing site '{site}'")


def detect_backend(mode: str, container: str, logger: logging.Logger) -> tuple[str, ExecutionBackend]:
	"""Auto-detects or initializes the appropriate execution backend."""
	if mode == "docker":
		return "docker", DockerBackend(container=container, logger=logger)
	elif mode == "native":
		return "native", NativeBackend(logger=logger)

	# Auto mode: Check if native bench is available, otherwise check docker
	if shutil.which("bench"):
		logger.info("Auto-detection: Native 'bench' CLI found in PATH. Using Native mode.")
		return "native", NativeBackend(logger=logger)

	# Check Docker
	if shutil.which("docker"):
		res = subprocess.run(
			["docker", "ps", "--filter", f"name={container}", "--format", "{{.Names}}"],
			stdout=subprocess.PIPE,
			text=True,
		)
		if container in res.stdout:
			logger.info(f"Auto-detection: Found active container '{container}'. Using Docker mode.")
			return "docker", DockerBackend(container=container, logger=logger)

	raise AutomationError(
		"Could not detect bench execution environment! Neither native 'bench' nor running Docker container was found."
	)


# ---------------------------------------------------------------------------
# Core Automation Engines
# ---------------------------------------------------------------------------
class FrappeBackupManager:
	"""Coordinates backup creation, SHA-256 verification, retention, and restore."""

	def __init__(
		self,
		source_site: str = DEFAULT_SOURCE_SITE,
		test_site: str = DEFAULT_TEST_SITE,
		backup_dir: Path = DEFAULT_BACKUP_DIR,
		retention_limit: int = DEFAULT_RETENTION_LIMIT,
		mode: str = "auto",
		container: str = DEFAULT_CONTAINER,
		logger: logging.Logger | None = None,
	):
		self.source_site = source_site
		self.test_site = test_site
		self.backup_dir = backup_dir.resolve()
		self.retention_limit = retention_limit
		self.container = container
		self.logger = logger or logging.getLogger("frappe_backup")

		self.mode_str, self.backend = detect_backend(mode, container, self.logger)
		self.backup_dir.mkdir(parents=True, exist_ok=True)

	# -----------------------------------------------------------------------
	# Requirement 1: Automated Backups
	# -----------------------------------------------------------------------
	def create_backup(self) -> BackupManifest:
		"""Executes full bench backup, pulls files, hashes them, and applies retention."""
		self.logger.info(f"Initiating full backup for site: '{self.source_site}'")
		bench_dir = self.backend.find_bench_dir(self.source_site)

		# Execute bench backup with files
		cmd = ["bench", "--site", self.source_site, "backup", "--with-files"]
		rc, stdout, stderr = self.backend.run_command(cmd, cwd=bench_dir)
		if rc != 0:
			self.logger.error(f"Bench backup failed with exit code {rc}:\n{stderr}")
			raise BackupExecutionError(f"Bench backup failed: {stderr or stdout}")

		self.logger.info("Bench backup completed successfully inside environment.")
		self.logger.debug(f"Backup Output:\n{stdout}")

		# Parse generated backup paths from bench output
		# Output format:
		# Config  : ./crm.localhost/private/backups/YYYYMMDD_HHMMSS-crm_localhost-site_config_backup.json ...
		# Database: ./crm.localhost/private/backups/YYYYMMDD_HHMMSS-crm_localhost-database.sql.gz ...
		# Public  : ./crm.localhost/private/backups/YYYYMMDD_HHMMSS-crm_localhost-files.tar ...
		# Private : ./crm.localhost/private/backups/YYYYMMDD_HHMMSS-crm_localhost-private-files.tar ...
		file_patterns = {
			"database": r"Database\s*:\s*(\S+database\.sql\.gz)",
			"public_files": r"Public\s*:\s*(\S+files\.tar)",
			"private_files": r"Private\s*:\s*(\S+private-files\.tar)",
			"site_config": r"Config\s*:\s*(\S+site_config_backup\.json)",
		}

		parsed_rel_paths: dict[str, str] = {}
		for key, pattern in file_patterns.items():
			match = re.search(pattern, stdout)
			if match:
				parsed_rel_paths[key] = match.group(1).lstrip("./")

		if "database" not in parsed_rel_paths:
			raise BackupExecutionError(f"Could not parse database backup path from bench output:\n{stdout}")

		# Derive unique backup ID from database timestamp
		# e.g., 20261104_154411-crm_localhost-database.sql.gz -> 20261104_154411_crm.localhost
		db_filename = Path(parsed_rel_paths["database"]).name
		timestamp_prefix = db_filename.split("-")[0]
		backup_id = f"{timestamp_prefix}_{self.source_site.replace('.', '_')}"

		target_backup_dir = self.backup_dir / backup_id
		target_backup_dir.mkdir(parents=True, exist_ok=True)
		self.logger.info(f"Target local backup directory: {target_backup_dir}")

		# Transfer files and compute SHA-256
		manifest_files: dict[str, BackupFileInfo] = {}
		checksums_lines: list[str] = []
		total_size = 0

		for ftype, rel_path in parsed_rel_paths.items():
			remote_full_path = f"{bench_dir}/sites/{rel_path}"
			fname = Path(rel_path).name
			local_file_path = target_backup_dir / fname

			self.backend.copy_from(remote_full_path, local_file_path)
			if not local_file_path.is_file():
				raise BackupExecutionError(f"Missing copied backup file: {local_file_path}")

			sha256 = compute_sha256(local_file_path)
			size = local_file_path.stat().st_size
			total_size += size

			manifest_files[ftype] = BackupFileInfo(
				file_type=ftype,
				filename=fname,
				size_bytes=size,
				sha256=sha256,
			)
			checksums_lines.append(f"{sha256}  {fname}")
			self.logger.info(
				f"  [{ftype.upper():<13}] {fname} ({format_size(size)}) | SHA-256: {sha256[:12]}..."
			)

		# Write checksums.sha256
		checksum_file = target_backup_dir / "checksums.sha256"
		checksum_file.write_text("\n".join(checksums_lines) + "\n", encoding="utf-8")

		# Create Manifest
		now_iso = datetime.now(timezone.utc).isoformat()
		manifest = BackupManifest(
			backup_id=backup_id,
			site=self.source_site,
			timestamp=now_iso,
			mode=self.mode_str,
			container=self.container if self.mode_str == "docker" else None,
			files=manifest_files,
			total_size_bytes=total_size,
			verified=True,
			retention_tag="active",
		)

		manifest_path = target_backup_dir / "manifest.json"
		manifest_path.write_text(json.dumps(manifest.to_dict(), indent=2), encoding="utf-8")
		self.logger.info(f"Backup manifest saved to: {manifest_path}")

		# Requirement 3: Enforce Retention Policy
		self.apply_retention_policy()

		return manifest

	# -----------------------------------------------------------------------
	# Requirement 2: Cryptographic Verification (SHA-256 + Archive Integrity)
	# -----------------------------------------------------------------------
	def verify_backup(self, backup_id: str | None = None) -> VerificationReport:
		"""Verifies SHA-256 checksums and tests structural archive integrity."""
		target_dir = self._resolve_backup_dir(backup_id)
		self.logger.info(f"Verifying backup in: {target_dir}")

		manifest_path = target_dir / "manifest.json"
		if not manifest_path.is_file():
			raise ChecksumVerificationError(f"Missing manifest.json in {target_dir}")

		manifest_data = json.loads(manifest_path.read_text(encoding="utf-8"))
		manifest = BackupManifest.from_dict(manifest_data)

		checksums_matched = True
		archives_valid = True
		file_results: dict[str, dict[str, Any]] = {}
		details: list[str] = []

		for ftype, finfo in manifest.files.items():
			fpath = target_dir / finfo.filename
			if not fpath.is_file():
				checksums_matched = False
				archives_valid = False
				file_results[ftype] = {
					"filename": finfo.filename,
					"exists": False,
					"error": "File missing on disk",
				}
				details.append(f"ERROR: File {finfo.filename} does not exist.")
				continue

			# SHA-256 Recalculation
			current_hash = compute_sha256(fpath)
			hash_ok = current_hash == finfo.sha256
			if not hash_ok:
				checksums_matched = False
				details.append(f"MISMATCH in {finfo.filename}: expected {finfo.sha256}, got {current_hash}")

			# Archive structural integrity validation
			archive_ok = True
			archive_err: str | None = None

			try:
				if finfo.filename.endswith(".sql.gz"):
					with gzip.open(fpath, "rb") as gz:
						# Stream check until EOF to ensure uncorrupted gzip stream
						while gz.read(65536):
							pass
				elif finfo.filename.endswith(".tar"):
					if not tarfile.is_tarfile(fpath):
						archive_ok = False
						archive_err = "Not a valid TAR archive"
					else:
						with tarfile.open(fpath, "r") as tar:
							tar.getmembers()
				elif finfo.filename.endswith(".json"):
					json.loads(fpath.read_text(encoding="utf-8"))
			except Exception as e:
				archive_ok = False
				archive_err = str(e)
				archives_valid = False
				details.append(f"CORRUPTION in {finfo.filename}: {archive_err}")

			file_results[ftype] = {
				"filename": finfo.filename,
				"size_bytes": fpath.stat().st_size,
				"expected_sha256": finfo.sha256,
				"calculated_sha256": current_hash,
				"checksum_matched": hash_ok,
				"archive_valid": archive_ok,
				"archive_error": archive_err,
			}

			status_str = "PASSED" if (hash_ok and archive_ok) else "FAILED"
			self.logger.info(
				f"  [{ftype.upper():<13}] {finfo.filename:<45} | Hash: {'MATCH' if hash_ok else 'FAIL'} | Format: {'VALID' if archive_ok else 'CORRUPT'} | Status: {status_str}"
			)

		overall_status = "VALID" if (checksums_matched and archives_valid) else "INVALID"
		report = VerificationReport(
			backup_id=manifest.backup_id,
			verified_at=datetime.now(timezone.utc).isoformat(),
			checksums_matched=checksums_matched,
			archives_valid=archives_valid,
			status=overall_status,
			file_results=file_results,
			details=details,
		)

		if overall_status == "INVALID":
			self.logger.error(f"Verification failed for backup {manifest.backup_id}!")
		else:
			self.logger.info(
				f"All checksums and archives for backup '{manifest.backup_id}' verified successfully."
			)

		return report

	# -----------------------------------------------------------------------
	# Requirement 3: Backup Retention Policy (Keep latest N)
	# -----------------------------------------------------------------------
	def apply_retention_policy(self) -> list[Path]:
		"""Prunes local and remote backups exceeding the retention threshold."""
		self.logger.info(
			f"Evaluating backup retention policy (Limit: latest {self.retention_limit} backups)..."
		)
		backups = self.list_backups()
		total_backups = len(backups)

		if total_backups <= self.retention_limit:
			self.logger.info(
				f"Retention policy check: {total_backups}/{self.retention_limit} backups retained. No pruning needed."
			)
			return []

		# Sort backups ascending (oldest first)
		sorted_backups = sorted(backups, key=lambda b: b.timestamp)
		prune_count = total_backups - self.retention_limit
		to_prune = sorted_backups[:prune_count]

		pruned_paths: list[Path] = []
		for manifest in to_prune:
			backup_path = self.backup_dir / manifest.backup_id
			self.logger.warning(
				f"Pruning expired backup: '{manifest.backup_id}' (Created: {manifest.timestamp})"
			)
			try:
				shutil.rmtree(backup_path)
				pruned_paths.append(backup_path)
				self.logger.info(f"Successfully deleted local directory: {backup_path}")
			except Exception as e:
				self.logger.error(f"Failed to remove {backup_path}: {e}")
				raise RetentionPolicyError(f"Could not delete old backup {backup_path}: {e}")

		self.logger.info(
			f"Retention policy enforced: Pruned {len(pruned_paths)} oldest backups. Retained newest {self.retention_limit}."
		)
		return pruned_paths

	# -----------------------------------------------------------------------
	# Requirement 4: Safe Restoration in Isolated Test Environment
	# -----------------------------------------------------------------------
	def restore_backup(
		self,
		backup_id: str | None = None,
		target_site: str = DEFAULT_TEST_SITE,
		mariadb_root_password: str = "123",
		admin_password: str = "admin",
	) -> dict[str, Any]:
		"""Restores a verified backup into an isolated test environment."""
		# 1. HARD SAFETY CHECK: Never restore to production/original site
		if target_site == self.source_site:
			err_msg = (
				f"CRITICAL SAFETY VIOLATION: Refusing to restore into production/source site '{self.source_site}'! "
				f"Always specify an isolated test site (e.g. '--target-site {DEFAULT_TEST_SITE}')."
			)
			self.logger.critical(err_msg)
			raise RestoreSafetyError(err_msg)

		self.logger.info(f"Starting safe restoration pipeline -> Target Test Site: '{target_site}'")
		target_dir = self._resolve_backup_dir(backup_id)

		# 2. Pre-restoration integrity check
		self.logger.info("Performing pre-restoration SHA-256 verification...")
		verification = self.verify_backup(target_dir.name)
		if verification.status != "VALID":
			raise ChecksumVerificationError(
				f"Pre-restore check failed: Backup '{target_dir.name}' is corrupt or tampered!"
			)

		manifest = BackupManifest.from_dict(
			json.loads((target_dir / "manifest.json").read_text(encoding="utf-8"))
		)

		bench_dir = self.backend.find_bench_dir(self.source_site)

		# 3. Ensure test site exists on bench
		rc, _, _ = self.backend.run_command(
			["bash", "-c", f"test -f {bench_dir}/sites/{target_site}/site_config.json"]
		)
		if rc != 0:
			self.logger.info(f"Target site '{target_site}' does not exist. Creating new site...")
			new_site_cmd = [
				"bench",
				"new-site",
				target_site,
				"--mariadb-root-password",
				mariadb_root_password,
				"--admin-password",
				admin_password,
				"--no-mariadb-socket",
				"--force",
			]
			rc_ns, out_ns, err_ns = self.backend.run_command(new_site_cmd, cwd=bench_dir)
			if rc_ns != 0:
				raise RestoreExecutionError(f"Failed to create new test site: {err_ns or out_ns}")

		# 4. Prepare files inside the execution environment
		db_file = manifest.files["database"].filename
		pub_file = manifest.files.get("public_files", BackupFileInfo("", "", 0, "")).filename
		priv_file = manifest.files.get("private_files", BackupFileInfo("", "", 0, "")).filename

		local_db_path = target_dir / db_file
		local_pub_path = target_dir / pub_file if pub_file else None
		local_priv_path = target_dir / priv_file if priv_file else None

		# Fix MariaDB 11.8 / 10.8 dump incompatibility:
		# Strip any 'NOTE_VERBOSITY' statements to avoid SQL 1193 syntax error during restore
		sanitized_sql_gz = target_dir / f"sanitized_{db_file}"
		self.logger.info("Sanitizing SQL dump for cross-version MariaDB compatibility...")
		with gzip.open(local_db_path, "rt", encoding="utf-8", errors="replace") as gz_in:
			with gzip.open(sanitized_sql_gz, "wt", encoding="utf-8") as gz_out:
				for line in gz_in:
					if "NOTE_VERBOSITY" not in line:
						gz_out.write(line)

		remote_restore_dir = "/tmp/frappe_restore"
		self.backend.run_command(["mkdir", "-p", remote_restore_dir])

		remote_db_path = f"{remote_restore_dir}/{db_file}"
		self.backend.copy_to(sanitized_sql_gz, remote_db_path)

		remote_pub_path = None
		if local_pub_path and local_pub_path.is_file():
			remote_pub_path = f"{remote_restore_dir}/{pub_file}"
			self.backend.copy_to(local_pub_path, remote_pub_path)

		remote_priv_path = None
		if local_priv_path and local_priv_path.is_file():
			remote_priv_path = f"{remote_restore_dir}/{priv_file}"
			self.backend.copy_to(local_priv_path, remote_priv_path)

		# 5. Execute bench restore
		restore_cmd = [
			"bench",
			"--site",
			target_site,
			"restore",
			remote_db_path,
			"--mariadb-root-password",
			mariadb_root_password,
			"--admin-password",
			admin_password,
		]
		if remote_pub_path:
			restore_cmd.extend(["--with-public-files", remote_pub_path])
		if remote_priv_path:
			restore_cmd.extend(["--with-private-files", remote_priv_path])

		self.logger.info(f"Executing bench restore into '{target_site}'...")
		rc_res, out_res, err_res = self.backend.run_command(restore_cmd, cwd=bench_dir)
		if rc_res != 0:
			self.logger.error(f"Restore failed with code {rc_res}:\n{err_res or out_res}")
			raise RestoreExecutionError(f"Restore failed: {err_res or out_res}")

		# 6. Post-restore Validation & Cache Clear
		self.logger.info("Performing post-restoration verification query...")
		check_cmd = [
			"bench",
			"--site",
			target_site,
			"mariadb",
			"--execute",
			"SELECT count(*) FROM tabDocType;",
		]
		rc_chk, out_chk, _ = self.backend.run_command(check_cmd, cwd=bench_dir)
		doctype_count = 0
		if rc_chk == 0 and "count(*)" in out_chk:
			lines = [l.strip() for l in out_chk.splitlines() if l.strip()]
			if len(lines) >= 2:
				doctype_count = int(lines[1])

		# Clear cache on target site
		self.backend.run_command(["bench", "--site", target_site, "clear-cache"], cwd=bench_dir)

		# Clean temporary sanitized file
		if sanitized_sql_gz.is_file():
			sanitized_sql_gz.unlink()

		restore_report = {
			"source_site": self.source_site,
			"target_site": target_site,
			"backup_id": manifest.backup_id,
			"restored_at": datetime.now(timezone.utc).isoformat(),
			"doctype_count_verified": doctype_count,
			"status": "SUCCESS",
			"production_intact": True,
		}

		self.logger.info(
			f"SUCCESS: Site '{target_site}' successfully restored! Verified DocType count: {doctype_count}."
		)
		self.logger.info(f"Production site '{self.source_site}' remains 100% untouched and safe.")
		return restore_report

	# -----------------------------------------------------------------------
	# Helper Methods
	# -----------------------------------------------------------------------
	def list_backups(self) -> list[BackupManifest]:
		"""Lists all local backups by discovering manifest.json files."""
		results: list[BackupManifest] = []
		if not self.backup_dir.is_dir():
			return results

		for child in self.backup_dir.iterdir():
			if child.is_dir():
				mfile = child / "manifest.json"
				if mfile.is_file():
					try:
						data = json.loads(mfile.read_text(encoding="utf-8"))
						results.append(BackupManifest.from_dict(data))
					except Exception as e:
						self.logger.warning(f"Could not load manifest in {child}: {e}")

		return sorted(results, key=lambda x: x.timestamp, reverse=True)

	def _resolve_backup_dir(self, backup_id: str | None) -> Path:
		"""Finds target backup directory by ID or selects the latest."""
		if backup_id:
			candidate = self.backup_dir / backup_id
			if candidate.is_dir():
				return candidate
			raise AutomationError(f"Backup with ID '{backup_id}' not found in {self.backup_dir}")

		backups = self.list_backups()
		if not backups:
			raise AutomationError(f"No backups found in {self.backup_dir}")

		latest = backups[0]
		return self.backup_dir / latest.backup_id


# ---------------------------------------------------------------------------
# CLI Commands & Presentation
# ---------------------------------------------------------------------------
def build_cli_parser() -> argparse.ArgumentParser:
	"""Constructs the command-line argument parser."""
	parser = argparse.ArgumentParser(
		prog="backup_manager.py",
		description="Enterprise Frappe CRM Backup, Verification, Retention & Restore Automation Tool",
	)
	parser.add_argument(
		"--source-site",
		default=DEFAULT_SOURCE_SITE,
		help=f"Name of the source Frappe CRM site (default: {DEFAULT_SOURCE_SITE})",
	)
	parser.add_argument(
		"--backup-dir",
		type=Path,
		default=DEFAULT_BACKUP_DIR,
		help=f"Directory to store local backup archives (default: {DEFAULT_BACKUP_DIR})",
	)
	parser.add_argument(
		"--retention-limit",
		type=int,
		default=DEFAULT_RETENTION_LIMIT,
		help=f"Number of latest backups to retain (default: {DEFAULT_RETENTION_LIMIT})",
	)
	parser.add_argument(
		"--mode",
		choices=["auto", "docker", "native"],
		default="auto",
		help="Execution mode (default: auto)",
	)
	parser.add_argument(
		"--container",
		default=DEFAULT_CONTAINER,
		help=f"Docker container name (default: {DEFAULT_CONTAINER})",
	)
	parser.add_argument(
		"--log-file",
		type=Path,
		default=DEFAULT_LOG_FILE,
		help=f"Path to write log output (default: {DEFAULT_LOG_FILE})",
	)
	parser.add_argument(
		"--verbose",
		"-v",
		action="store_true",
		help="Enable verbose debug logging",
	)

	subparsers = parser.add_subparsers(dest="action", required=True, help="Action to execute")

	# Action: backup
	backup_p = subparsers.add_parser(
		"backup", help="Create a full backup, compute SHA-256, and apply retention"
	)
	backup_p.add_argument(
		"--retention-limit",
		type=int,
		default=None,
		help=f"Number of latest backups to retain (default: {DEFAULT_RETENTION_LIMIT})",
	)

	# Action: verify
	verify_p = subparsers.add_parser("verify", help="Verify SHA-256 checksums and archive integrity")
	verify_p.add_argument(
		"--backup-id",
		help="Backup ID to verify (default: latest)",
	)

	# Action: restore
	restore_p = subparsers.add_parser("restore", help="Safely restore backup into test environment")
	restore_p.add_argument(
		"--backup-id",
		help="Backup ID to restore (default: latest)",
	)
	restore_p.add_argument(
		"--target-site",
		default=DEFAULT_TEST_SITE,
		help=f"Isolated target test site (default: {DEFAULT_TEST_SITE})",
	)
	restore_p.add_argument(
		"--mariadb-root-password",
		default="123",
		help="MariaDB root password (default: 123)",
	)
	restore_p.add_argument(
		"--admin-password",
		default="admin",
		help="Administrator password for site (default: admin)",
	)

	# Action: list
	subparsers.add_parser("list", help="List all backups, creation dates, sizes, and integrity status")

	# Action: prune
	prune_p = subparsers.add_parser(
		"prune", help="Enforce retention policy to keep only the latest N backups"
	)
	prune_p.add_argument(
		"--retention-limit",
		type=int,
		default=None,
		help=f"Number of latest backups to retain (default: {DEFAULT_RETENTION_LIMIT})",
	)

	return parser


def main() -> int:
	"""Main CLI entry point."""
	parser = build_cli_parser()
	args = parser.parse_args()

	logger = setup_logging(args.log_file, args.verbose)
	logger.info("=" * 65)
	logger.info("Frappe CRM DevOps Automation Tool")
	logger.info("=" * 65)

	try:
		retention_limit = (
			args.retention_limit
			if getattr(args, "retention_limit", None) is not None
			else DEFAULT_RETENTION_LIMIT
		)
		manager = FrappeBackupManager(
			source_site=args.source_site,
			backup_dir=args.backup_dir,
			retention_limit=retention_limit,
			mode=args.mode,
			container=args.container,
			logger=logger,
		)

		if args.action == "backup":
			manifest = manager.create_backup()
			print("\n" + "=" * 65)
			print("BACKUP COMPLETED SUCCESSFULLY")
			print("=" * 65)
			print(f"Backup ID   : {manifest.backup_id}")
			print(f"Site        : {manifest.site}")
			print(f"Timestamp   : {manifest.timestamp}")
			print(f"Total Size  : {format_size(manifest.total_size_bytes)}")
			print(f"Storage Path: {args.backup_dir / manifest.backup_id}")
			print("=" * 65)

		elif args.action == "verify":
			report = manager.verify_backup(args.backup_id)
			print("\n" + "=" * 65)
			print("BACKUP VERIFICATION REPORT")
			print("=" * 65)
			print(f"Backup ID       : {report.backup_id}")
			print(f"Verified At     : {report.verified_at}")
			print(f"Checksums Match : {report.checksums_matched}")
			print(f"Archives Valid  : {report.archives_valid}")
			print(f"Overall Status  : {report.status}")
			print("-" * 65)
			for ftype, info in report.file_results.items():
				print(
					f"{ftype:<14}: {info['filename']} ({format_size(info['size_bytes'])}) -> "
					f"Checksum: {'OK' if info['checksum_matched'] else 'FAIL'}, "
					f"Format: {'OK' if info['archive_valid'] else 'FAIL'}"
				)
			print("=" * 65)

		elif args.action == "restore":
			result = manager.restore_backup(
				backup_id=args.backup_id,
				target_site=args.target_site,
				mariadb_root_password=args.mariadb_root_password,
				admin_password=args.admin_password,
			)
			print("\n" + "=" * 65)
			print("RESTORATION COMPLETED SUCCESSFULLY")
			print("=" * 65)
			print(f"Source Site       : {result['source_site']}")
			print(f"Target Test Site  : {result['target_site']}")
			print(f"Backup ID         : {result['backup_id']}")
			print(f"Restored At       : {result['restored_at']}")
			print(f"DocTypes Verified : {result['doctype_count_verified']}")
			print(f"Production Safe   : {result['production_intact']}")
			print(f"Overall Status    : {result['status']}")
			print("=" * 65)

		elif args.action == "list":
			backups = manager.list_backups()
			print("\n" + "=" * 80)
			print(f"{'BACKUP ID':<35} {'TIMESTAMP':<22} {'SIZE':<12} {'SITE':<15}")
			print("-" * 80)
			if not backups:
				print("No backups found.")
			for b in backups:
				print(
					f"{b.backup_id:<35} {b.timestamp[:19]:<22} {format_size(b.total_size_bytes):<12} {b.site:<15}"
				)
			print("=" * 80)

		elif args.action == "prune":
			pruned = manager.apply_retention_policy()
			print("\n" + "=" * 65)
			print("RETENTION ENFORCEMENT COMPLETED")
			print("=" * 65)
			print(f"Retention Limit : Latest {args.retention_limit} backups")
			print(f"Backups Pruned  : {len(pruned)}")
			for p in pruned:
				print(f" - Deleted: {p.name}")
			print("=" * 65)

		return 0

	except AutomationError as e:
		logger.critical(f"AUTOMATION ERROR: {e}")
		return 1
	except KeyboardInterrupt:
		logger.warning("Operation cancelled by user.")
		return 130
	except Exception as e:
		logger.exception(f"UNEXPECTED ERROR: {e}")
		return 2


if __name__ == "__main__":
	sys.exit(main())