
import subprocess
import logging
import hashlib
import json
import argparse
from pathlib import Path

# Frappe configuration
CONTAINER_NAME = "crm-frappe-1"
SITE_NAME = "crm-task1.localhost"

BENCH_DIR = "/home/frappe/frappe-bench"
CONTAINER_BACKUP_DIR = (
    f"{BENCH_DIR}/sites/{SITE_NAME}/private/backups"
)

# Store persistent backup copies on the Windows host
# Project directory (task2-backup-restore)
PROJECT_DIR = Path(__file__).resolve().parent.parent

# Store persistent backup copies on the Windows host
BACKUP_ROOT = PROJECT_DIR / "backups"

# Logging configuration
LOG_DIR = PROJECT_DIR / "logs"
LOG_DIR.mkdir(parents=True, exist_ok=True)

logging.basicConfig(
    filename=LOG_DIR / "backup.log",
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)



def run_command(command, interactive=False):
    """Execute a command and report failures."""

    return subprocess.run(
        command,
        capture_output=not interactive,
        text=True,
        check=True
    )



def generate_checksum(file_path):
    """Generate SHA-256 checksum using Python."""
    sha256 = hashlib.sha256()

    with open(file_path, "rb") as file:
        for chunk in iter(lambda: file.read(4096), b""):
            sha256.update(chunk)

    return sha256.hexdigest()


def apply_retention_policy():
    """Keep only the latest 7 backup sets in the container."""

    command = [
        "docker", "exec", CONTAINER_NAME,
        "bash", "-lc",
        f"find {CONTAINER_BACKUP_DIR} -maxdepth 1 "
        "-type f -name '*-database.sql.gz' "
        "-printf '%f\\n' | sort -r"
    ]

    try:
        result = run_command(command)
        database_backups = [
            name for name in result.stdout.splitlines() if name
        ]

        old_backups = database_backups[7:]

        site_slug = SITE_NAME.replace(".", "_")

        for database_file in old_backups:
            suffix = f"-{site_slug}-database.sql.gz"
            timestamp = database_file.removesuffix(suffix)

            delete_command = [
                "docker", "exec", CONTAINER_NAME,
                "bash", "-lc",
                f"rm -f {CONTAINER_BACKUP_DIR}/"
                f"{timestamp}-{site_slug}-*"
            ]

            run_command(delete_command)
            logging.info("Removed old backup set: %s", timestamp)

        print(
            f"Container retention applied. "
            f"Backup sets found: {len(database_backups)}"
        )

    except subprocess.CalledProcessError as error:
        logging.error("Retention failed: %s", error.stderr)
        print("Retention policy failed:", error.stderr)


def create_backup():
    """Create, copy and checksum a complete backup set."""

    command = [
        "docker", "exec", CONTAINER_NAME,
        "bash", "-lc",
        f"cd {BENCH_DIR} && "
        f"bench --site {SITE_NAME} backup --with-files"
    ]

    try:
        result = run_command(command)
        print(result.stdout)

        # Find the latest database backup
        list_command = [
            "docker", "exec", CONTAINER_NAME,
            "bash", "-lc",
            f"ls -1t {CONTAINER_BACKUP_DIR}/*-database.sql.gz "
            "| head -n 1"
        ]

        database_path = run_command(list_command).stdout.strip()

        if not database_path:
            raise RuntimeError("No database backup was found.")

        database_name = Path(database_path).name
        site_slug = SITE_NAME.replace(".", "_")
        suffix = f"-{site_slug}-database.sql.gz"
        timestamp = database_name.removesuffix(suffix)

        # Create a separate folder for this backup set
        local_backup_dir = BACKUP_ROOT / timestamp
        local_backup_dir.mkdir(parents=True, exist_ok=True)

        backup_files = [
            f"{timestamp}-{site_slug}-database.sql.gz",
            f"{timestamp}-{site_slug}-site_config_backup.json",
            f"{timestamp}-{site_slug}-files.tar",
            f"{timestamp}-{site_slug}-private-files.tar"
        ]

        # Copy all four files from Docker to Windows
        for filename in backup_files:
            source = f"{CONTAINER_BACKUP_DIR}/{filename}"
            destination = local_backup_dir / filename

            run_command([
                "docker", "cp",
                f"{CONTAINER_NAME}:{source}",
                str(destination)
            ])

        # Generate and save SHA-256 checksums
        checksums = {}

        print("\nSHA-256 Checksums:")

        for filename in backup_files:
            file_path = local_backup_dir / filename
            checksum = generate_checksum(file_path)

            checksums[filename] = checksum
            print(f"{checksum}  {filename}")

        manifest = {
            "timestamp": timestamp,
            "site": SITE_NAME,
            "algorithm": "SHA-256",
            "checksums": checksums
        }

        manifest_path = local_backup_dir / "checksum_manifest.json"

        with open(manifest_path, "w", encoding="utf-8") as file:
            json.dump(manifest, file, indent=4)

        logging.info("Backup completed: %s", timestamp)
        print(f"\nBackup copied to: {local_backup_dir}")
        print("Checksum manifest saved successfully.")

        # Apply retention after safely copying the backup
        apply_retention_policy()

    except (subprocess.CalledProcessError, RuntimeError, OSError) as error:
        logging.error("Backup failed: %s", error)
        print("Backup failed:", error)


def verify_backup(timestamp=None):
    """Verify backup files against their saved SHA-256 manifest."""

    try:
        if timestamp:
            backup_dir = BACKUP_ROOT / timestamp
        else:
            backup_dirs = sorted(
                path for path in BACKUP_ROOT.iterdir()
                if path.is_dir()
            )

            if not backup_dirs:
                print("No local backups found.")
                return False

            backup_dir = backup_dirs[-1]

        if not backup_dir.is_dir():
            print("Backup directory not found:", backup_dir)
            return False

        manifest_path = backup_dir / "checksum_manifest.json"

        with open(manifest_path, encoding="utf-8") as file:
            manifest = json.load(file)

        print(f"\nVerifying backup: {backup_dir.name}")

        all_valid = True

        for filename, expected_hash in manifest["checksums"].items():
            file_path = backup_dir / filename

            if not file_path.is_file():
                print(f"MISSING: {filename}")
                all_valid = False
                continue

            actual_hash = generate_checksum(file_path)

            if actual_hash == expected_hash:
                print(f"PASS: {filename}")
            else:
                print(f"FAIL: {filename} - checksum mismatch")
                all_valid = False

        if all_valid:
            print("\nBackup verification successful.")
            logging.info("Verification passed: %s", backup_dir.name)
            return True

        print("\nBackup verification failed.")
        logging.error("Verification failed: %s", backup_dir.name)
        return False

    except (OSError, KeyError, json.JSONDecodeError) as error:
        logging.error("Verification error: %s", error)
        print("Verification error:", error)
        return False




def restore_backup(timestamp, target_site):
    """Restore a backup into a separate test site."""

    # Safety: never restore over the original source site
    if target_site == SITE_NAME:
        print("ERROR: Cannot restore over the original source site.")
        return
    if not verify_backup(timestamp):
        print("Restore aborted: backup integrity verification failed.")
        return
    backup_dir = BACKUP_ROOT / timestamp

    if not backup_dir.is_dir():
        print("Backup directory not found:", backup_dir)
        return

    site_slug = SITE_NAME.replace(".", "_")

    database_file = (
        f"{timestamp}-{site_slug}-database.sql.gz"
    )
    public_file = (
        f"{timestamp}-{site_slug}-files.tar"
    )
    private_file = (
        f"{timestamp}-{site_slug}-private-files.tar"
    )

    database_path = backup_dir / database_file
    public_path = backup_dir / public_file
    private_path = backup_dir / private_file

    required_files = [
        database_path,
        public_path,
        private_path
    ]

    for file_path in required_files:
        if not file_path.is_file():
            print("Required backup file missing:", file_path)
            return

    

    print(
        f"\nRestore target: {target_site}\n"
        f"Backup timestamp: {timestamp}"
    )

    confirmation = input(
        "Type RESTORE to continue: "
    )

    if confirmation != "RESTORE":
        print("Restore cancelled.")
        return

    container_tmp = "/tmp/task2-restore"
    fixed_sql = f"{container_tmp}/database-fixed.sql.gz"

    try:
        run_command([
            "docker", "exec", CONTAINER_NAME,
            "mkdir", "-p", container_tmp
        ])

        # Copy SQL backup to container
        run_command([
            "docker", "cp",
            str(database_path),
            f"{CONTAINER_NAME}:{container_tmp}/database.sql.gz"
        ])

        # Remove only the incompatible NOTE_VERBOSITY statement
        run_command([
            "docker", "exec", CONTAINER_NAME,
            "bash", "-lc",
            f"gzip -dc {container_tmp}/database.sql.gz "
            f"| sed '/NOTE_VERBOSITY/d' "
            f"| gzip > {fixed_sql}"
        ])

        # Copy public and private file archives
        run_command([
            "docker", "cp",
            str(public_path),
            f"{CONTAINER_NAME}:{container_tmp}/public-files.tar"
        ])

        run_command([
            "docker", "cp",
            str(private_path),
            f"{CONTAINER_NAME}:{container_tmp}/private-files.tar"
        ])

        # Restore database and files into the existing target site
        restore_command = [
            "docker", "exec", "-it", CONTAINER_NAME,
            "bash", "-lc",
            f"cd {BENCH_DIR} && "
            f"bench --site {target_site} restore {fixed_sql} "
            f"--with-public-files {container_tmp}/public-files.tar "
            f"--with-private-files {container_tmp}/private-files.tar"
        ]

        run_command(restore_command, interactive=True)

        
        logging.info(
            "Restore completed for %s from %s",
            target_site, timestamp
        )
        print("Restore completed successfully.")

    except subprocess.CalledProcessError as error:
        logging.error("Restore failed: %s", error.stderr)
        print("Restore failed:", error.stderr)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Frappe CRM Backup Automation Tool"
    )

    parser.add_argument(
        "action",
        choices=["backup", "verify", "retention", "restore"],
        help="Operation to perform"
    )

    parser.add_argument(
        "--timestamp",
        help="Backup timestamp to verify"
    )
    parser.add_argument(
        "--target-site",
        help="Separate site to restore into"
    )
    args = parser.parse_args()

    if args.action == "backup":
        create_backup()

    elif args.action == "verify":
        verify_backup(args.timestamp)

    elif args.action == "retention":
        apply_retention_policy()

    elif args.action == "restore":
        if not args.timestamp or not args.target_site:
            parser.error(
                "restore requires --timestamp and --target-site"
            )

                 
        restore_backup(args.timestamp, args.target_site)
