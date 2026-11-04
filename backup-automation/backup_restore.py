#!/usr/bin/env python3

import argparse
import hashlib
import json
import logging
import os
import subprocess
import sys
from datetime import datetime
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
LOG_FOLDER = SCRIPT_DIR / "logs"
REPORT_FOLDER = SCRIPT_DIR / "reports"
CHECKSUM_END = "-checksums.json"


def sha256_of_file(path):
    sha = hashlib.sha256()
    with open(path, "rb") as f:
        while True:
            chunk = f.read(1024 * 1024)
            if not chunk:
                break
            sha.update(chunk)
    return sha.hexdigest()


def run_bench(bench_args, bench_dir, password=None):
    command = ["bench", *bench_args]
    text = " ".join(command)
    if password:
        text = text.replace(password, "********")
    logging.info("Running: %s", text)
    try:
        subprocess.run(command, cwd=bench_dir, check=True)
    except FileNotFoundError:
        raise RuntimeError("bench not found. Run this inside the Frappe container.")
    except subprocess.CalledProcessError as error:
        raise RuntimeError("bench failed with exit code " + str(error.returncode))


def get_backup_folder(args):
    return Path(args.bench_dir) / "sites" / args.site / "private" / "backups"


def find_backups(folder):
    backups = {}
    for file in sorted(folder.iterdir()):
        is_backup_file = file.is_file() and file.name[:8].isdigit()
        if is_backup_file and not file.name.endswith(CHECKSUM_END):
            backup_id = file.name.split("-")[0]
            if backup_id not in backups:
                backups[backup_id] = []
            backups[backup_id].append(file)
    return backups


def list_backup_ids(folder):
    ids = []
    for file in folder.glob("*" + CHECKSUM_END):
        ids.append(file.name[: -len(CHECKSUM_END)])
    return sorted(ids)


def choose_backup_id(folder, wanted):
    ids = list_backup_ids(folder)
    if not ids:
        raise RuntimeError("No backups found. Run the backup command first.")
    if wanted == "latest":
        return ids[-1]
    if wanted not in ids:
        raise RuntimeError("Backup " + wanted + " not found. Use 'list' to see IDs.")
    return wanted


def save_report(filename, lines):
    REPORT_FOLDER.mkdir(exist_ok=True)
    path = REPORT_FOLDER / filename
    path.write_text("\n".join(lines) + "\n")
    logging.info("Report saved: %s", path)


def do_backup(args):
    folder = get_backup_folder(args)
    folder.mkdir(parents=True, exist_ok=True)
    ids_before = set(find_backups(folder))

    run_bench(["--site", args.site, "backup", "--with-files"], args.bench_dir)

    new_ids = sorted(set(find_backups(folder)) - ids_before)
    if not new_ids:
        raise RuntimeError("Backup finished but no new files were found.")

    backup_id = new_ids[-1]
    files = find_backups(folder)[backup_id]
    if len(files) < 3:
        raise RuntimeError("Expected 3 files (database, public, private) but found " + str(len(files)))

    checksums = {}
    for file in files:
        checksums[file.name] = sha256_of_file(file)

    (folder / (backup_id + CHECKSUM_END)).write_text(json.dumps(checksums, indent=2))

    lines = [
        "Backup Report",
        "Time: " + datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "Site: " + args.site,
        "Backup ID: " + backup_id,
        "Status: SUCCESS",
        "Files:",
    ]

    for name in checksums:
        lines.append("  " + name + "  sha256=" + checksums[name])

    save_report("backup_report_" + backup_id + ".txt", lines)
    do_verify(args, backup_id)
    do_cleanup(args)


def do_verify(args, wanted_id):
    folder = get_backup_folder(args)
    backup_id = choose_backup_id(folder, wanted_id)
    saved = json.loads((folder / (backup_id + CHECKSUM_END)).read_text())

    all_ok = True
    result_lines = []

    for name in saved:
        path = folder / name
        if not path.exists():
            status = "MISSING"
        elif sha256_of_file(path) != saved[name]:
            status = "FAIL"
        else:
            status = "PASS"

        if status != "PASS":
            all_ok = False

        logging.info("%s: %s", name, status)
        result_lines.append("  [" + status + "] " + name)

    lines = [
        "Verification Report",
        "Time: " + datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "Backup ID: " + backup_id,
        "Result: " + ("PASSED" if all_ok else "FAILED"),
        *result_lines,
    ] 

    save_report("verification_report_" + backup_id + ".txt", lines)

    if not all_ok:
        raise RuntimeError("Verification FAILED for backup " + backup_id)

    logging.info("Verification PASSED for backup %s", backup_id)
    return backup_id


def do_cleanup(args):
    folder = get_backup_folder(args)
    ids = list_backup_ids(folder)
    old_ids = ids[: len(ids) - args.keep] if len(ids) > args.keep else []

    for backup_id in old_ids:
        for file in find_backups(folder).get(backup_id, []):
            file.unlink()

        checksum_file = folder / (backup_id + CHECKSUM_END)
        if checksum_file.exists():
            checksum_file.unlink()

        logging.info("Retention: removed old backup %s", backup_id)


def do_list(args):
    for backup_id in list_backup_ids(get_backup_folder(args)):
        print(backup_id)


def do_restore(args):
    if args.test_site == args.site:
        raise RuntimeError("Refusing to restore over the original site. Use a different --test-site.")

    test_site_config = Path(args.bench_dir) / "sites" / args.test_site / "site_config.json"
    if not test_site_config.exists():
        raise RuntimeError("Test site '" + args.test_site + "' does not exist. Create it with 'bench new-site'.")

    backup_id = do_verify(args, args.id)

    db_file = public_file = private_file = None

    for file in find_backups(get_backup_folder(args))[backup_id]:
        if "database" in file.name:
            db_file = file
        elif "private-files" in file.name:
            private_file = file
        elif "-files." in file.name:
            public_file = file

    bench_args = [
        "--site", args.test_site, "restore", str(db_file),
        "--with-public-files", str(public_file),
        "--with-private-files", str(private_file),
    ]

    password = os.environ.get("MYSQL_ROOT_PASSWORD")
    if password:
        bench_args += ["--db-root-password", password]

    run_bench(bench_args, args.bench_dir, password)

    save_report("restore_report_" + backup_id + ".txt", [
        "Restore Report",
        "Time: " + datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "Backup ID: " + backup_id,
        "Source site: " + args.site,
        "Test site: " + args.test_site,
        "Status: SUCCESS",
    ])

    logging.info("Restore of %s into %s completed", backup_id, args.test_site)


def main():
    parser = argparse.ArgumentParser(description="Frappe CRM backup & restore tool")
    parser.add_argument("--bench-dir", default=os.environ.get("FRAPPE_BENCH_DIR", "/home/frappe/frappe-bench"))
    parser.add_argument("--site", default=os.environ.get("FRAPPE_SITE", "crm.localhost"))
    commands = parser.add_subparsers(dest="action", required=True)

    backup_cmd = commands.add_parser("backup", help="backup + verify + keep latest 7")
    backup_cmd.add_argument("--keep", type=int, default=7)

    commands.add_parser("list", help="list backups")

    verify_cmd = commands.add_parser("verify", help="verify checksums")
    verify_cmd.add_argument("--id", default="latest")

    cleanup_cmd = commands.add_parser("cleanup", help="apply retention only")
    cleanup_cmd.add_argument("--keep", type=int, default=7)

    restore_cmd = commands.add_parser("restore", help="restore into a separate test site")
    restore_cmd.add_argument("--id", default="latest")
    restore_cmd.add_argument("--test-site", required=True)

    args = parser.parse_args()

    LOG_FOLDER.mkdir(exist_ok=True)

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler(LOG_FOLDER / "backup_tool.log"),
        ],
    )

    try:
        if args.action == "backup":
            do_backup(args)
        elif args.action == "list":
            do_list(args)
        elif args.action == "verify":
            do_verify(args, args.id)
        elif args.action == "cleanup":
            do_cleanup(args)
        elif args.action == "restore":
            do_restore(args)
    except Exception as error:
        logging.error("%s", error)
        sys.exit(1)


if __name__ == "__main__":
    main()