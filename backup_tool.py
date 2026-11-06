import argparse
import gzip
import hashlib
import json
import re
import shutil
import subprocess
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent
COMPOSE_FILE = ROOT / "docker" / "docker-compose.yml"
BENCH_DIR = "/home/frappe/frappe-bench"
SITE = "crm.localhost"
CONTAINER_BACKUPS = f"{BENCH_DIR}/sites/{SITE}/private/backups"
BACKUP_ROOT = Path.home() / "FrappeCRMBackups" / "crm_localhost"


class BackupVerificationError(RuntimeError):
	"""Raised when a backup manifest or one of its files is invalid."""


def run_compose(*args: str) -> subprocess.CompletedProcess[str]:
	"""Run Docker Compose from this repository and report command failures."""
	return subprocess.run(
		["docker", "compose", "-f", str(COMPOSE_FILE), *args],
		cwd=ROOT,
		check=True,
		capture_output=True,
		text=True,
	)


def list_container_backups() -> set[str]:
	result = run_compose(
		"exec",
		"-T",
		"-w",
		BENCH_DIR,
		"frappe",
		"ls",
		"-1",
		f"sites/{SITE}/private/backups",
	)
	return {line.strip() for line in result.stdout.splitlines() if line.strip()}


def sha256_file(file_path: Path) -> str:
	digest = hashlib.sha256()
	with file_path.open("rb") as backup_file:
		for chunk in iter(lambda: backup_file.read(1024 * 1024), b""):
			digest.update(chunk)
	return digest.hexdigest()


def make_mariadb_10_8_compatible(dump_path: Path) -> None:
	temporary_path = dump_path.with_name(dump_path.name + ".tmp")
	removed_lines = 0

	try:
		with (
			gzip.open(dump_path, "rt", encoding="utf-8") as source,
			gzip.open(temporary_path, "wt", encoding="utf-8") as destination,
		):
			for line in source:
				if "/*M!100616 SET" in line and "NOTE_VERBOSITY" in line:
					removed_lines += 1
				else:
					destination.write(line)

		if removed_lines != 2:
			raise RuntimeError(f"Expected 2 NOTE_VERBOSITY statements, found {removed_lines}.")

		temporary_path.replace(dump_path)
	finally:
		temporary_path.unlink(missing_ok=True)


def write_manifest(backup_dir: Path) -> Path:
	files = sorted(
		file_path
		for file_path in backup_dir.iterdir()
		if file_path.is_file() and file_path.name != "manifest.json"
	)
	if not files:
		raise BackupVerificationError(f"No backup files found in {backup_dir}")

	manifest = {
		"backup_id": backup_dir.name,
		"source_site": SITE,
		"files": [
			{
				"filename": file_path.name,
				"size_bytes": file_path.stat().st_size,
				"sha256": sha256_file(file_path),
			}
			for file_path in files
		],
	}

	manifest_path = backup_dir / "manifest.json"
	manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
	return manifest_path


def verify_backup(backup_dir: Path) -> None:
	manifest_path = backup_dir / "manifest.json"
	try:
		manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
	except (OSError, json.JSONDecodeError) as error:
		raise BackupVerificationError(f"Cannot read manifest {manifest_path}: {error}") from error

	if not isinstance(manifest, dict) or not isinstance(manifest.get("files"), list):
		raise BackupVerificationError(f"Invalid manifest structure: {manifest_path}")
	if not manifest["files"]:
		raise BackupVerificationError(f"Manifest contains no file records: {manifest_path}")

	expected_names: set[str] = set()
	for record in manifest["files"]:
		if not isinstance(record, dict):
			raise BackupVerificationError("Invalid file record in manifest.")

		filename = record.get("filename")
		expected_hash = record.get("sha256")
		expected_size = record.get("size_bytes")
		if (
			not isinstance(filename, str)
			or Path(filename).name != filename
			or not isinstance(expected_hash, str)
			or not isinstance(expected_size, int)
		):
			raise BackupVerificationError(f"Invalid file record in manifest: {record!r}")
		if filename in expected_names:
			raise BackupVerificationError(f"Duplicate file in manifest: {filename}")
		expected_names.add(filename)

		file_path = backup_dir / filename
		if not file_path.is_file():
			raise BackupVerificationError(f"Backup file is missing: {filename}")
		actual_size = file_path.stat().st_size
		if actual_size != expected_size:
			raise BackupVerificationError(
				f"Size mismatch for {filename}: expected {expected_size}, found {actual_size}"
			)
		actual_hash = sha256_file(file_path)
		if actual_hash != expected_hash:
			raise BackupVerificationError(f"SHA-256 mismatch for {filename}")

	actual_names = {
		file_path.name
		for file_path in backup_dir.iterdir()
		if file_path.is_file() and file_path.name != "manifest.json"
	}
	if actual_names != expected_names:
		unexpected = sorted(actual_names - expected_names)
		raise BackupVerificationError(f"Backup contains files not listed in manifest: {unexpected}")


def get_restore_files(backup_dir: Path) -> dict[str, Path]:
	manifest = json.loads((backup_dir / "manifest.json").read_text(encoding="utf-8"))

	database = []
	public_files = []
	private_files = []

	for record in manifest["files"]:
		filename = record["filename"]

		if filename.endswith("-database.sql.gz"):
			database.append(backup_dir / filename)
		elif filename.endswith("-private-files.tar"):
			private_files.append(backup_dir / filename)
		elif filename.endswith("-files.tar"):
			public_files.append(backup_dir / filename)

	if len(database) != 1 or len(public_files) != 1 or len(private_files) != 1:
		raise BackupVerificationError(
			"Backup must contain exactly one database, public-files, and private-files archive."
		)

	return {
		"database": database[0],
		"public_files": public_files[0],
		"private_files": private_files[0],
	}


def stage_restore_files(backup_dir: Path, target_site: str) -> dict[str, str]:
	restore_files = get_restore_files(backup_dir)
	staging_dir = f"/tmp/fcrm_restore_{target_site}"

	run_compose("exec", "-T", "frappe", "mkdir", "-p", staging_dir)

	staged_paths = {}
	for file_type, host_path in restore_files.items():
		container_path = f"{staging_dir}/{host_path.name}"
		run_compose(
			"cp",
			str(host_path),
			f"frappe:{container_path}",
		)
		staged_paths[file_type] = container_path

	return staged_paths


def validate_target_site(target_site: str) -> None:
	if target_site == SITE:
		raise ValueError("Refusing to restore over the source CRM site.")
	if not re.fullmatch(r"test_[a-z0-9_]+\.localhost", target_site):
		raise ValueError("Target site must look like test_restore.localhost.")


def site_exists(target_site: str) -> bool:
	result = run_compose(
		"exec",
		"-T",
		"-w",
		BENCH_DIR,
		"frappe",
		"sh",
		"-lc",
		f"if [ -e sites/{target_site} ]; then printf EXISTS; else printf NOT_FOUND; fi",
	)
	return result.stdout.strip() == "EXISTS"


def find_backup(backup_id: str | None) -> Path:
	if backup_id:
		backup_dir = BACKUP_ROOT / backup_id
		if not backup_dir.is_dir():
			raise BackupVerificationError(f"Backup set not found: {backup_dir}")
		return backup_dir

	candidates = (
		[path for path in BACKUP_ROOT.iterdir() if path.is_dir() and (path / "manifest.json").is_file()]
		if BACKUP_ROOT.exists()
		else []
	)
	if not candidates:
		raise BackupVerificationError(f"No backup manifests found under {BACKUP_ROOT}")
	return max(candidates, key=lambda path: path.name)


def list_backups(backup_root: Path = BACKUP_ROOT) -> int:
	if not backup_root.exists():
		print(f"No backups found under {backup_root}")
		return 0

	backups = sorted(
		(path for path in backup_root.iterdir() if path.is_dir() and (path / "manifest.json").is_file()),
		key=lambda path: path.name,
		reverse=True,
	)

	if not backups:
		print(f"No backups found under {backup_root}")
		return 0

	invalid_found = False
	for backup_dir in backups:
		try:
			verify_backup(backup_dir)
		except (OSError, BackupVerificationError) as error:
			print(f"INVALID  {backup_dir.name}: {error}")
			invalid_found = True
		else:
			print(f"VERIFIED {backup_dir.name}")

	return 1 if invalid_found else 0


def prune_backups(backup_root: Path = BACKUP_ROOT, keep: int = 7) -> list[Path]:
	"""Keep the newest verified, manifested backup sets under the given root."""
	if keep < 1:
		raise ValueError("Retention count must be at least 1.")
	if not backup_root.exists():
		return []

	backup_dirs = sorted(
		(
			path
			for path in backup_root.iterdir()
			if path.is_dir()
			and re.fullmatch(r"\d{8}_\d{6}_\d{6}", path.name)
			and (path / "manifest.json").is_file()
		),
		key=lambda path: path.name,
		reverse=True,
	)

	# Validate every managed set before deleting any, so corruption can't cause
	# a partially applied retention run.
	for backup_dir in backup_dirs:
		verify_backup(backup_dir)

	removed: list[Path] = []
	for backup_dir in backup_dirs[keep:]:
		shutil.rmtree(backup_dir)
		removed.append(backup_dir)
		print(f"Removed old backup set: {backup_dir.name}")
	return removed


def create_backup() -> Path:
	"""Create a Bench backup and copy only its new files outside the repository."""
	existing_files = list_container_backups()

	run_compose(
		"exec",
		"-T",
		"-w",
		BENCH_DIR,
		"frappe",
		"bench",
		"--site",
		SITE,
		"backup",
		"--with-files",
	)

	new_files = sorted(list_container_backups() - existing_files)
	if not new_files:
		raise RuntimeError("Bench completed, but no new backup files were found.")

	backup_id = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
	backup_dir = BACKUP_ROOT / backup_id
	backup_dir.mkdir(parents=True, exist_ok=False)

	for filename in new_files:
		if Path(filename).name != filename:
			raise RuntimeError(f"Unexpected backup filename: {filename}")

		run_compose(
			"cp",
			f"frappe:{CONTAINER_BACKUPS}/{filename}",
			str(backup_dir),
		)
		print(f"Copied: {filename}")

	database_dumps = list(backup_dir.glob("*-database.sql.gz"))
	if len(database_dumps) != 1:
		raise RuntimeError(f"Expected exactly one database dump, found {len(database_dumps)}.")

	make_mariadb_10_8_compatible(database_dumps[0])
	manifest_path = write_manifest(backup_dir)
	print(f"Manifest written: {manifest_path}")
	verify_backup(backup_dir)
	print(f"Verification passed: {backup_dir}")
	prune_backups()
	print(f"Backup saved to: {backup_dir}")
	return backup_dir


def main():
	parser = argparse.ArgumentParser(description="Backup and restore the local Frappe CRM site")
	commands = parser.add_subparsers(dest="command", required=True)

	commands.add_parser("backup")
	verify_parser = commands.add_parser("verify")
	verify_parser.add_argument(
		"--backup-id",
		help="Backup folder name; defaults to the newest backup with a manifest",
	)
	commands.add_parser("list-backups")
	restore_parser = commands.add_parser("restore")
	restore_parser.add_argument(
		"--target-site",
		required=True,
		help="New test site, for example test_restore.localhost",
	)
	restore_parser.add_argument(
		"--backup-id",
		help="Backup folder name; defaults to the newest verified backup",
	)
	args = parser.parse_args()

	if args.command == "list-backups":
		return list_backups()

	if args.command == "backup":
		try:
			create_backup()
		except (
			OSError,
			RuntimeError,
			ValueError,
			subprocess.CalledProcessError,
		) as error:
			detail = getattr(error, "stderr", None) or str(error)
			print(f"Backup failed: {detail.strip()}", file=sys.stderr)
			return 1
		return 0

	if args.command == "verify":
		try:
			backup_dir = find_backup(args.backup_id)
			verify_backup(backup_dir)
		except (OSError, BackupVerificationError) as error:
			print(f"Verification failed: {error}", file=sys.stderr)
			return 1
		print(f"Verification passed: {backup_dir}")
		return 0
	if args.command == "restore":
		try:
			validate_target_site(args.target_site)
			if site_exists(args.target_site):
				raise ValueError(f"Target site already exists: {args.target_site}")

			backup_dir = find_backup(args.backup_id)
			verify_backup(backup_dir)
			restore_files = stage_restore_files(backup_dir, args.target_site)

			run_compose(
				"exec",
				"-T",
				"-w",
				BENCH_DIR,
				"frappe",
				"bench",
				"new-site",
				args.target_site,
				"--mariadb-root-password",
				"123",
				"--admin-password",
				"admin",
				"--no-mariadb-socket",
			)

			result = run_compose(
				"exec",
				"-T",
				"-w",
				BENCH_DIR,
				"frappe",
				"bench",
				"--site",
				args.target_site,
				"restore",
				restore_files["database"],
				"--mariadb-root-password",
				"123",
				"--with-public-files",
				restore_files["public_files"],
				"--with-private-files",
				restore_files["private_files"],
			)
		except (
			OSError,
			BackupVerificationError,
			ValueError,
			subprocess.CalledProcessError,
		) as error:
			details = []
			if isinstance(error, subprocess.CalledProcessError):
				if error.stdout:
					details.append(error.stdout.strip())
				if error.stderr:
					details.append(error.stderr.strip())

			detail = "\n".join(details) or str(error)
			print(f"Restore failed: {detail}", file=sys.stderr)
			return 1

		if result.stdout.strip():
			print(result.stdout.strip())
		print(f"Restore completed for test site {args.target_site}.")
		return 0

	parser.error(f"{args.command} is not implemented yet")
	return 2


if __name__ == "__main__":
	raise SystemExit(main())
