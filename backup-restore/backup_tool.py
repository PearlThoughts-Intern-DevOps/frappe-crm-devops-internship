import argparse
import gzip
import hashlib
import json
import logging
import shutil
import subprocess
import sys
import tempfile
import getpass
from datetime import datetime
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
CONFIG = json.loads((BASE_DIR / "config.json").read_text())

BACKUP_DIR = BASE_DIR / CONFIG["backup_root"]
REPORT_DIR = BASE_DIR / CONFIG["reports_dir"]
LOG_DIR = BASE_DIR / CONFIG["logs_dir"]

for folder in (BACKUP_DIR, REPORT_DIR, LOG_DIR):
    folder.mkdir(parents=True, exist_ok=True)

logging.basicConfig(
    filename=LOG_DIR / "backup_tool.log",
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)

CONTAINER = CONFIG["docker_container"]
BENCH = CONFIG["bench_path"]
SOURCE = CONFIG["source_site"]
TEST = CONFIG["test_site"]


def docker(command, check=True):
    result = subprocess.run(
        ["docker", *command],
        text=True,
        capture_output=True
    )
    if check and result.returncode != 0:
        raise RuntimeError(result.stderr or result.stdout)
    return result


def sha256(file_path):
    digest = hashlib.sha256()
    with open(file_path, "rb") as file:
        for chunk in iter(lambda: file.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def backup():
    logging.info("Starting backup for %s", SOURCE)

    command = (
        f"cd {BENCH} && bench --site {SOURCE} backup"
        + (" --with-files" if CONFIG["backup_with_files"] else "")
        + (" --compress" if CONFIG["compress_files"] else "")
    )

    result = docker(["exec", CONTAINER, "bash", "-lc", command])
    print(result.stdout)

    find_command = (
        f"find {CONFIG['container_backup_path']} "
        "-maxdepth 1 -type f -name '*-database.sql*' "
        "-printf '%T@ %p\\n' | sort -nr | head -1"
    )
    result = docker(["exec", CONTAINER, "bash", "-lc", find_command])

    if not result.stdout.strip():
        raise RuntimeError("Could not locate the generated database backup.")

    database_path = result.stdout.strip().split(" ", 1)[1]

    backup_id = Path(database_path).name.split("-database.sql")[0]
    destination = BACKUP_DIR / backup_id
    destination.mkdir(parents=True, exist_ok=True)

    files_to_copy = [database_path]

    for suffix in ("-files.tgz", "-private-files.tgz"):
        candidate = (
            f"{CONFIG['container_backup_path']}/{backup_id}{suffix}"
        )
        check = docker(
            ["exec", CONTAINER, "test", "-f", candidate],
            check=False
        )
        if check.returncode == 0:
            files_to_copy.append(candidate)

    copied = []

    for source_path in files_to_copy:
        filename = Path(source_path).name
        target = destination / filename

        docker(["cp", f"{CONTAINER}:{source_path}", str(target)])

        copied.append({
            "file": filename,
            "sha256": sha256(target),
            "size_bytes": target.stat().st_size
        })

    manifest = {
        "backup_id": backup_id,
        "source_site": SOURCE,
        "created_at": datetime.now().astimezone().isoformat(),
        "files": copied
    }

    (destination / "manifest.json").write_text(
        json.dumps(manifest, indent=4)
    )

    print(f"\nBackup saved: {destination}")
    logging.info("Backup completed: %s", backup_id)

    verify(backup_id)
    cleanup()


def verify(backup_id=None):
    folders = (
        [BACKUP_DIR / backup_id]
        if backup_id else
        sorted(
            [p for p in BACKUP_DIR.iterdir() if p.is_dir()],
            key=lambda p: p.name,
            reverse=True
        )
    )

    if not folders:
        print("No backups found.")
        return

    all_passed = True

    for folder in folders:
        manifest_path = folder / "manifest.json"

        if not manifest_path.exists():
            print(f"FAIL: Missing manifest in {folder.name}")
            all_passed = False
            continue

        manifest = json.loads(manifest_path.read_text())
        checks = []

        for item in manifest["files"]:
            path = folder / item["file"]
            passed = path.exists() and sha256(path) == item["sha256"]

            checks.append({
                "file": item["file"],
                "status": "PASS" if passed else "FAIL"
            })

            if not passed:
                all_passed = False

        report = {
            "backup_id": folder.name,
            "verified_at": datetime.now().astimezone().isoformat(),
            "overall_status": (
                "PASS"
                if checks and all(x["status"] == "PASS" for x in checks)
                else "FAIL"
            ),
            "checks": checks
        }

        report_path = REPORT_DIR / f"{folder.name}-verification.json"
        report_path.write_text(json.dumps(report, indent=4))

        print(json.dumps(report, indent=4))

    logging.info(
        "Verification result: %s",
        "PASS" if all_passed else "FAIL"
    )

    if not all_passed:
        raise RuntimeError("One or more backup verification checks failed.")


def list_backups():
    folders = sorted(
        [p for p in BACKUP_DIR.iterdir() if p.is_dir()],
        key=lambda p: p.name,
        reverse=True
    )

    if not folders:
        print("No backups found.")
        return

    for folder in folders:
        print(folder.name)


def cleanup():
    folders = sorted(
        [p for p in BACKUP_DIR.iterdir() if p.is_dir()],
        key=lambda p: p.name,
        reverse=True
    )

    keep = int(CONFIG["retention_count"])

    for folder in folders[keep:]:
        manifest = folder / "manifest.json"

        if not manifest.exists():
            continue

        shutil.rmtree(folder)
        logging.info("Removed old backup: %s", folder.name)
        print(f"Removed old backup: {folder.name}")


def restore(backup_id):
    folder = BACKUP_DIR / backup_id
    manifest_path = folder / "manifest.json"

    if not manifest_path.exists():
        raise RuntimeError("Backup manifest not found.")

    # Verify backup before restoring.
    verify(backup_id)

    manifest = json.loads(manifest_path.read_text())

    database = next(
        (
            folder / item["file"]
            for item in manifest["files"]
            if "-database.sql" in item["file"]
        ),
        None
    )

    if database is None or not database.exists():
        raise RuntimeError("Database backup file not found.")

    print(f"Restore target: {TEST}")
    print("The original site will NOT be modified.")

    root_password = getpass.getpass("MariaDB root password: ")

    # Check whether the separate test site already exists.
    sites_command = f"cd {BENCH} && test -d sites/{TEST}"

    exists = docker(
        ["exec", CONTAINER, "bash", "-lc", sites_command],
        check=False
    )

    if exists.returncode != 0:
        admin_password = getpass.getpass(
            "New test-site admin password: "
        )

        create_command = (
            f"cd {BENCH} && bench new-site {TEST} "
            "--db-host mariadb --db-root-username root "
            "--db-root-password \"$DB_ROOT_PASSWORD\" "
            "--admin-password \"$ADMIN_PASSWORD\" "
            "--install-app crm"
        )

        docker([
            "exec",
            "-e", f"DB_ROOT_PASSWORD={root_password}",
            "-e", f"ADMIN_PASSWORD={admin_password}",
            CONTAINER,
            "bash",
            "-lc",
            create_command
        ])

    # Create a temporary MariaDB 10.8-compatible SQL backup.
    # The original verified backup is never modified.
    with tempfile.NamedTemporaryFile(
        suffix=".sql.gz",
        dir=folder,
        delete=False
    ) as temp_file:
        compatible_database = Path(temp_file.name)

    removed_lines = 0

    try:
        with gzip.open(
            database,
            "rt",
            encoding="utf-8",
            errors="replace"
        ) as source:

            with gzip.open(
                compatible_database,
                "wt",
                encoding="utf-8"
            ) as target:

                for line in source:
                    if "NOTE_VERBOSITY" in line:
                        removed_lines += 1
                        continue

                    target.write(line)

        if removed_lines == 0:
            logging.info("No NOTE_VERBOSITY lines required removal.")
        else:
            logging.info(
                "Removed %s incompatible NOTE_VERBOSITY lines.",
                removed_lines
            )

        container_database = f"/tmp/{compatible_database.name}"

        docker([
            "cp",
            str(compatible_database),
            f"{CONTAINER}:{container_database}"
        ])

        restore_command = (
            f"cd {BENCH} && bench --site {TEST} restore "
            f"{container_database} "
            "--db-root-username root "
            "--db-root-password \"$DB_ROOT_PASSWORD\" --force"
        )

        public_files = next(
            (
                folder / item["file"]
                for item in manifest["files"]
                if item["file"].endswith("-files.tgz")
            ),
            None
        )

        private_files = next(
            (
                folder / item["file"]
                for item in manifest["files"]
                if item["file"].endswith("-private-files.tgz")
            ),
            None
        )

        if public_files:
            docker([
                "cp",
                str(public_files),
                f"{CONTAINER}:/tmp/{public_files.name}"
            ])

            restore_command += (
                f" --with-public-files /tmp/{public_files.name}"
            )

        if private_files:
            docker([
                "cp",
                str(private_files),
                f"{CONTAINER}:/tmp/{private_files.name}"
            ])

            restore_command += (
                f" --with-private-files /tmp/{private_files.name}"
            )

        docker([
            "exec",
            "-e", f"DB_ROOT_PASSWORD={root_password}",
            CONTAINER,
            "bash",
            "-lc",
            restore_command
        ])

        print(f"Restore completed into {TEST}")
        logging.info("Restore completed into %s", TEST)

    finally:
        compatible_database.unlink(missing_ok=True)

        docker(
            ["exec", CONTAINER, "rm", "-f", f"/tmp/{compatible_database.name}"],
            check=False
        )


def main():
    parser = argparse.ArgumentParser(
        description="Frappe CRM Backup and Restore Automation Tool"
    )

    sub = parser.add_subparsers(
        dest="action",
        required=True
    )

    sub.add_parser("backup")
    sub.add_parser("verify")
    sub.add_parser("list")
    sub.add_parser("cleanup")

    restore_parser = sub.add_parser("restore")
    restore_parser.add_argument("backup_id")

    args = parser.parse_args()

    try:
        if args.action == "backup":
            backup()
        elif args.action == "verify":
            verify()
        elif args.action == "list":
            list_backups()
        elif args.action == "cleanup":
            cleanup()
        elif args.action == "restore":
            restore(args.backup_id)

    except Exception as error:
        logging.exception("Operation failed")
        print(f"ERROR: {error}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()