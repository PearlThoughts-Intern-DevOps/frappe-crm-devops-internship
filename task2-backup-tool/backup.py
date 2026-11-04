import argparse
import hashlib
import logging
import os
import shutil
import subprocess
import sys
from datetime import datetime
from pathlib import Path
 
SITE = os.environ.get("FRAPPE_SITE", "crm.localhost")
CONTAINER = os.environ.get("FRAPPE_CONTAINER", "crm-frappe-1")   # "local" = run bench on this machine
BENCH = os.environ.get("FRAPPE_BENCH_PATH", "/home/frappe/frappe-bench")
BACKUPS = Path("backups")      # in .gitignore
REPORTS = Path("reports")
KEEP = 7
 
logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s",
                    handlers=[logging.StreamHandler(), logging.FileHandler("backup.log")])
log = logging.getLogger()
 
 
def run(container, cmd, env=()):
    """Run a shell command in the bench folder (inside a container, or locally)."""
    if container == "local":
        args = ["bash", "-c", f"cd {BENCH} && {cmd}"]
    else:
        args = ["docker", "exec"] + [x for e in env for x in ("-e", e)] + [container, "bash", "-c", f"cd {BENCH} && {cmd}"]
    return subprocess.run(args, check=True, capture_output=True, text=True).stdout
 
 
def copy_out(container, remote, local):
    if container == "local":
        shutil.copy2(remote, local)
    else:
        subprocess.run(["docker", "cp", f"{container}:{remote}", str(local)], check=True, capture_output=True)
 
 
def copy_in(container, folder, remote_dir):
    if container == "local":
        shutil.copytree(folder, remote_dir, dirs_exist_ok=True)
    else:
        subprocess.run(["docker", "cp", f"{folder}/.", f"{container}:{remote_dir}"], check=True, capture_output=True)
 
 
def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()
 
 
def write_report(name, status, lines):
    REPORTS.mkdir(exist_ok=True)
    text = f"{name}\nStatus: {status}\nTime: {datetime.now():%Y-%m-%d %H:%M:%S}\n\n" + "\n".join(lines) + "\n"
    (REPORTS / f"{name}.txt").write_text(text)
 
 
def verify(folder):
    """Compare every file against SHA256SUMS. Returns True if all match."""
    lines, ok = [], True
    for line in (folder / "SHA256SUMS").read_text().splitlines():
        expected, name = line.split("  ", 1)
        f = folder / name
        good = f.exists() and sha256(f) == expected
        ok &= good
        lines.append(f"{'OK      ' if good else 'MISMATCH'}  {name}")
    log.info("Verify %s: %s", folder.name, "PASS" if ok else "FAIL")
    write_report(f"verify_{folder.name}", "PASS" if ok else "FAIL", lines)
    return ok
 
 
def prune():
    old = sorted(d for d in BACKUPS.iterdir() if (d / "SHA256SUMS").exists())[:-KEEP]
    for d in old:
        shutil.rmtree(d)
        log.info("Retention: deleted %s", d.name)
 
 
def backup(_):
    log.info("Running bench backup")
    run(CONTAINER, f"bench --site {SITE} backup --with-files")
    remote_dir = f"{BENCH}/sites/{SITE}/private/backups"
    names = sorted(run(CONTAINER, f"ls -1 {remote_dir}").split())
    stamp = names[-1][:15]                                   # e.g. 20261104_131616
    files = [n for n in names if n.startswith(stamp)]
    folder = BACKUPS / stamp
    folder.mkdir(parents=True)
    sums = []
    for n in files:
        copy_out(CONTAINER, f"{remote_dir}/{n}", folder / n)
        sums.append(f"{sha256(folder / n)}  {n}")
    (folder / "SHA256SUMS").write_text("\n".join(sums) + "\n")
    log.info("Backup saved in %s (%d files)", folder, len(files))
    if not verify(folder):
        return 1
    write_report(f"backup_{stamp}", "SUCCESS", sums)
    prune()
    return 0
 
 
def pick(backup_id):
    folders = sorted(d for d in BACKUPS.iterdir() if (d / "SHA256SUMS").exists())
    if not folders:
        raise SystemExit("No backups found")
    return BACKUPS / backup_id if backup_id else folders[-1]
 
 
def verify_cmd(args):
    return 0 if verify(pick(args.backup_id)) else 1
 
 
def restore(args):
    if args.test_container == CONTAINER:
        raise SystemExit("Refusing: test container must differ from the source container")
    if "FRAPPE_DB_ROOT_PASSWORD" not in os.environ:
        raise SystemExit("Set FRAPPE_DB_ROOT_PASSWORD (test database root password)")
    folder = pick(args.backup_id)
    if not verify(folder):
        raise SystemExit("Backup failed verification, not restoring")
    tmp = f"/tmp/restore-{folder.name}"
    run(args.test_container, f"mkdir -p {tmp}")
    copy_in(args.test_container, folder, tmp)
    names = [p.name for p in folder.iterdir()]
    db = next(n for n in names if n.endswith("database.sql.gz"))
    cmd = f"bench --site {args.test_site} --force restore {tmp}/{db}"
    for n in names:
        if n.endswith("-private-files.tar"):
            cmd += f" --with-private-files {tmp}/{n}"
        elif n.endswith("-files.tar"):
            cmd += f" --with-public-files {tmp}/{n}"
    run(args.test_container, cmd + ' --db-root-password "$FRAPPE_DB_ROOT_PASSWORD"', env=["FRAPPE_DB_ROOT_PASSWORD"])
    run(args.test_container, f"bench --site {args.test_site} clear-cache")
    log.info("Restore into %s finished", args.test_site)
    write_report(f"restore_{folder.name}", "SUCCESS", [f"Restored {folder.name} into {args.test_site} in {args.test_container}"])
    return 0
 
 
def main():
    p = argparse.ArgumentParser(description="Frappe CRM backup & restore")
    sub = p.add_subparsers(dest="cmd", required=True)
    sub.add_parser("backup").set_defaults(func=backup)
    v = sub.add_parser("verify")
    v.add_argument("backup_id", nargs="?")
    v.set_defaults(func=verify_cmd)
    r = sub.add_parser("restore")
    r.add_argument("backup_id", nargs="?")
    r.add_argument("--test-container", required=True)
    r.add_argument("--test-site", default="restore-test.localhost")
    r.set_defaults(func=restore)
    args = p.parse_args()
    BACKUPS.mkdir(exist_ok=True)
    try:
        return args.func(args)
    except subprocess.CalledProcessError as e:
        log.error("Command failed: %s", (e.stderr or e.stdout or str(e)).strip()[-500:])
        return 2
    except Exception as e:
        log.error("%s: %s", type(e).__name__, e)
        return 2
 
 
if __name__ == "__main__":
    sys.exit(main())