


import argparse
import hashlib
import logging
import shlex
import shutil
import subprocess
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent
BACKUPS, LOGS, COMPOSE = ROOT / "backups", ROOT / "logs", ROOT.parent / "docker"
SITE, TEST_SITE, KEEP, DB_ROOT_PASSWORD = "crm.localhost", "crm-test.localhost", 7, "123"
CONTAINER_PATH = f"/home/frappe/frappe-bench/sites/{SITE}/private/backups"
EXEC = ["docker", "compose", "exec", "-T", "frappe", "bash", "-lc"]

BACKUPS.mkdir(exist_ok=True)
LOGS.mkdir(exist_ok=True)
logging.basicConfig(filename=LOGS / "backup.log", level=logging.INFO,
                    format="%(asctime)s %(levelname)s %(message)s")


def run(command):
    result = subprocess.run(command, cwd=COMPOSE, capture_output=True, text=True)
    output = "\n".join(x for x in (result.stdout, result.stderr) if x.strip())
    if result.returncode:
        logging.error("Command failed: %s\n%s", command, output)
        raise RuntimeError(f"Command failed (exit {result.returncode}):\n{output}")
    return output


def backup_folder(value):
    path = Path(value)
    resolved = (path if path.is_absolute() else BACKUPS / path).resolve()
    if BACKUPS.resolve() not in resolved.parents:
        raise RuntimeError("Backup folder must be inside backup-automation/backups")
    return resolved


def safe_file(folder, name):
    if not name or Path(name).name != name or name in {".", ".."}:
        raise RuntimeError(f"Unsafe backup filename: {name!r}")
    root, candidate = folder.resolve(), folder.resolve() / name
    if candidate.is_symlink() or candidate.resolve().parent != root:
        raise RuntimeError(f"File path escapes backup folder: {name}")
    return candidate


def sha256(path):
    digest = hashlib.sha256()
    # Path is validated by safe_file before this read.
    with open(path, "rb") as stream:  # nosemgrep: frappe-security-file-traversal
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def generate_checksums(folder):
    lines = [f"{sha256(safe_file(folder, p.name))}  {p.name}"
             for p in sorted(folder.iterdir())
             if p.is_file() and p.name != "checksums.sha256"]
    safe_file(folder, "checksums.sha256").write_text(
        "\n".join(lines) + "\n", encoding="utf-8")


def verify(folder):
    folder = backup_folder(folder)
    lines = safe_file(folder, "checksums.sha256").read_text(encoding="utf-8").splitlines()
    valid = True
    for line in lines:
        try:
            expected, name = line.split("  ", 1)
            path = safe_file(folder, name)
            ok = path.is_file() and sha256(path) == expected
        except (ValueError, RuntimeError):
            name, ok = line, False
        print(f"{'VERIFIED' if ok else 'FAILED'}: {name}")
        valid &= ok
    print("Verification successful" if valid else "Verification failed")
    return valid


def apply_retention(directory=BACKUPS):
    folders = sorted((p for p in directory.iterdir()
                      if p.is_dir() and not p.is_symlink()),
                     key=lambda p: p.name, reverse=True)
    for old in folders[KEEP:]:
        shutil.rmtree(safe_file(directory, old.name))
    print(f"Retention complete. Kept {min(len(folders), KEEP)} backups.")


def backup():
    folder = BACKUPS / datetime.now().strftime("%Y%m%d_%H%M%S")
    try:
        find_cmd = ["docker", "compose", "exec", "-T", "frappe", "bash", "-lc",
                    f"find {shlex.quote(CONTAINER_PATH)} -maxdepth 1 -type f -printf '%f\\n'"]
        before = set(run(find_cmd).splitlines())
        bench_cmd = f"cd /home/frappe/frappe-bench && bench --site {SITE} backup --with-files"
        run(["docker", "compose", "exec", "-T", "frappe", "bash", "-lc", bench_cmd])
        after = set(run(find_cmd).splitlines())
        suffixes = ("database.sql.gz", "files.tar", "private-files.tar", "site_config_backup.json")
        files = [name for name in after - before if name.endswith(suffixes)]
        if len(files) != 4:
            raise RuntimeError("Expected four new backup files")
        folder.mkdir()
        for name in files:
            run(["docker", "compose", "cp", f"frappe:{CONTAINER_PATH}/{name}", str(folder)])
        generate_checksums(folder)
        if not verify(folder): raise RuntimeError("Backup verification failed")
        apply_retention()
        logging.info("Backup completed: %s", folder)
        print(f"Backup completed: {folder}")
    except Exception as error:
        logging.exception("Backup failed")
        if folder.exists():
            shutil.rmtree(folder)
        print(f"Backup failed: {error}")


def restore(folder):
    folder = backup_folder(folder)
    if not folder.is_dir() or not verify(folder):
        raise RuntimeError("Invalid backup; restore cancelled")
    db = list(folder.glob("*-crm_localhost-database.sql.gz"))
    public = list(folder.glob("*-crm_localhost-files.tar"))
    private = list(folder.glob("*-crm_localhost-private-files.tar"))
    if len(db) != 1 or len(public) != 1 or len(private) != 1:
        raise RuntimeError("Exactly one database, public and private archive required")

    bench, site_path = "/home/frappe/frappe-bench", "/home/frappe/frappe-bench/sites/" + TEST_SITE
    exists_cmd = f"test -d {shlex.quote(site_path)} && echo EXISTS || echo MISSING"
    exists = run([*EXEC, exists_cmd]).strip()
    if exists == "EXISTS":
        raise RuntimeError(f"{TEST_SITE} already exists. Refusing to overwrite it.")

    create_cmd = f"""cd {bench} && bench new-site {TEST_SITE} --db-host mariadb
        --db-root-username root --db-root-password {DB_ROOT_PASSWORD}
        --admin-password admin --mariadb-user-host-login-scope='%'"""
    run([*EXEC, create_cmd])
    for path in (db[0], public[0], private[0]):
        safe_file(folder, path.name)
        run(["docker", "compose", "cp", str(path), f"frappe:/tmp/{path.name}"])

    source = f"/tmp/{db[0].name}"
    fixed = source.replace(".sql.gz", "-compatible.sql.gz")
    patch_cmd = f"""set -euo pipefail
        gzip -cd {shlex.quote(source)} | sed '/NOTE_VERBOSITY/d' | gzip -c > {shlex.quote(fixed)}
        if gzip -cd {shlex.quote(fixed)} | grep -q 'NOTE_VERBOSITY'; then
            echo 'Incompatible SQL setting remains' >&2; exit 1
        fi"""
    run([*EXEC, patch_cmd])
    restore_cmd = f"""cd {bench} && bench --site {TEST_SITE} restore {shlex.quote(fixed)}
        --db-root-username root --db-root-password {DB_ROOT_PASSWORD} --force
        --with-public-files /tmp/{public[0].name}
        --with-private-files /tmp/{private[0].name}"""
    print(run([*EXEC, restore_cmd]))
    logging.info("Restore completed to %s", TEST_SITE)
    print(f"Database and files restored to {TEST_SITE}")
    print("Original crm.localhost was not modified.")


def main():
    parser = argparse.ArgumentParser(description="Frappe CRM Backup Automation")
    parser.add_argument("action", choices=["backup", "verify", "list", "restore", "retention-test"])
    parser.add_argument("--folder")
    args = parser.parse_args()
    try:
        if args.action == "backup":
            backup()
        elif args.action == "list":
            folders = sorted((p for p in BACKUPS.iterdir() if p.is_dir()), reverse=True)
            print("\n".join(p.name for p in folders) if folders else "No backups found")
        elif args.action == "verify":
            if not args.folder:
                raise ValueError("Provide --folder")
            if not verify(args.folder):
                raise RuntimeError("Verification failed")
        elif args.action == "restore":
            if not args.folder:
                raise ValueError("Provide --folder")
            restore(args.folder)
        elif args.action == "retention-test":
            test = ROOT / "retention-test"
            test.mkdir(exist_ok=True)
            for i in range(1, 9):
                (test / f"test_backup_{i}").mkdir(exist_ok=True)
            apply_retention(test)
            print("Remaining:", sorted(p.name for p in test.iterdir()))
    except Exception as error:
        logging.exception("Operation failed")
        print(f"Error: {error}")


if __name__ == "__main__":
    main()
