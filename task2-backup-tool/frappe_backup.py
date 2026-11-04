#!/usr/bin/env python3
"""Backup & Restore automation tool for Frappe CRM.

Wraps Frappe Bench commands (``bench --site <site> backup --with-files`` and
``bench --site <site> restore``) and adds SHA-256 verification, a retention
policy, restore into a *separate* test environment, logging and a CLI.

The tool never touches the Frappe CRM application code. Database credentials
are read from the environment (FRAPPE_DB_ROOT_PASSWORD) and are never written
to disk, logs or reports.
"""
from __future__ import annotations

import argparse
import gzip
import hashlib
import json
import logging
import os
import re
import shlex
import shutil
import subprocess
import sys
import tarfile
from datetime import datetime, timezone
from logging.handlers import RotatingFileHandler
from pathlib import Path

__version__ = "1.0.0"

log = logging.getLogger("frappe_backup")

EXIT_OK = 0
EXIT_VERIFY_FAILED = 1
EXIT_ERROR = 2

PASSWORD_ENV = "FRAPPE_DB_ROOT_PASSWORD"

# Names bench produces, e.g. 20261104_101500-crm.localhost-database.sql.gz
BACKUP_FILE_RE = re.compile(
    r"^(?P<ts>\d{8}_\d{6})-(?P<site>.+?)-"
    r"(?P<kind>database\.sql\.gz|private-files\.tar(?:\.gz)?|"
    r"files\.tar(?:\.gz)?|site_config_backup\.json)$"
)


class ToolError(Exception):
    """Expected, user-facing failure (bad input, failed command, ...)."""


# --------------------------------------------------------------------------
# Helpers
# --------------------------------------------------------------------------
def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def sha256_file(path: Path, chunk: int = 1024 * 1024) -> str:
    digest = hashlib.sha256()
    with open(path, "rb") as fh:
        for block in iter(lambda: fh.read(chunk), b""):
            digest.update(block)
    return digest.hexdigest()


def human_size(num: int) -> str:
    size = float(num)
    for unit in ("B", "KB", "MB", "GB"):
        if size < 1024 or unit == "GB":
            return f"{size:.1f} {unit}" if unit != "B" else f"{int(size)} B"
        size /= 1024
    return f"{num} B"


def run_host(cmd: list[str], timeout: int = 3600) -> subprocess.CompletedProcess:
    """Run a command on the host (docker cp, docker inspect, ...)."""
    log.debug("host exec: %s", " ".join(shlex.quote(c) for c in cmd))
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
    except FileNotFoundError as exc:
        raise ToolError(f"Required program not found: {exc.filename}") from exc
    except subprocess.TimeoutExpired as exc:
        raise ToolError(f"Command timed out after {timeout}s: {cmd[0]}") from exc
    if proc.returncode != 0:
        tail = (proc.stderr or proc.stdout).strip().splitlines()[-10:]
        raise ToolError(f"Command failed (exit {proc.returncode}): {' '.join(cmd[:3])}\n" + "\n".join(tail))
    return proc


class Runner:
    """Runs shell commands in a bench directory, inside a container or locally."""

    def __init__(self, container: str | None, bench_path: str):
        self.container = container
        self.bench_path = bench_path.rstrip("/")

    def sh(self, shell_cmd: str, pass_env: tuple[str, ...] = (), timeout: int = 3600) -> str:
        inner = f"cd {shlex.quote(self.bench_path)} && {shell_cmd}"
        if self.container:
            cmd = ["docker", "exec"]
            for name in pass_env:
                cmd += ["-e", name]  # value is inherited from our environment, never on the command line
            cmd += [self.container, "bash", "-c", inner]
        else:
            cmd = ["bash", "-c", inner]
        log.debug("exec in %s: %s", self.container or "local", shell_cmd)
        return run_host(cmd, timeout=timeout).stdout

    def copy_from(self, remote: str, local: Path) -> None:
        if self.container:
            run_host(["docker", "cp", f"{self.container}:{remote}", str(local)])
        else:
            shutil.copy2(remote, local)

    def copy_to(self, local: Path, remote_dir: str) -> None:
        if self.container:
            run_host(["docker", "cp", str(local), f"{self.container}:{remote_dir}/"])
        else:
            shutil.copy2(local, remote_dir)

    def remote_sha256(self, remote: str) -> str:
        out = self.sh(f"sha256sum {shlex.quote(remote)}")
        return out.split()[0]

    def ensure_running(self) -> None:
        if not self.container:
            return
        out = run_host(["docker", "inspect", "-f", "{{.State.Running}}", self.container]).stdout.strip()
        if out != "true":
            raise ToolError(f"Container '{self.container}' is not running.")


# --------------------------------------------------------------------------
# Reports
# --------------------------------------------------------------------------
def write_report(reports_dir: Path, filename: str, title: str, meta: dict, headers: list[str],
                 rows: list[list[str]], status: str, notes: list[str] | None = None) -> Path:
    reports_dir.mkdir(parents=True, exist_ok=True)
    lines = [f"# {title}", "", f"**Status: {status}**", ""]
    for key, value in meta.items():
        lines.append(f"- **{key}:** {value}")
    lines += ["", "| " + " | ".join(headers) + " |", "|" + "|".join("---" for _ in headers) + "|"]
    for row in rows:
        lines.append("| " + " | ".join(str(c) for c in row) + " |")
    if notes:
        lines += ["", "## Notes", ""] + [f"- {n}" for n in notes]
    lines.append("")
    path = reports_dir / filename
    path.write_text("\n".join(lines), encoding="utf-8")
    log.info("Report written: %s", path)
    return path


# --------------------------------------------------------------------------
# Backup inventory
# --------------------------------------------------------------------------
def list_backups(backup_dir: Path, site: str | None = None) -> list[Path]:
    """Backup directories that contain a manifest, oldest first."""
    if not backup_dir.exists():
        return []
    found = []
    for d in backup_dir.iterdir():
        manifest = d / "manifest.json"
        if not (d.is_dir() and manifest.exists()):
            continue
        if site:
            try:
                if json.loads(manifest.read_text()).get("site") != site:
                    continue
            except (OSError, json.JSONDecodeError):
                continue
        found.append(d)
    return sorted(found, key=lambda p: p.name)


def resolve_backup(backup_dir: Path, site: str, backup_id: str) -> Path:
    backups = list_backups(backup_dir, site)
    if not backups:
        raise ToolError(f"No backups found for site '{site}' in {backup_dir}")
    if backup_id == "latest":
        return backups[-1]
    path = backup_dir / backup_id
    if path not in backups:
        raise ToolError(f"Backup '{backup_id}' not found. Available: {', '.join(b.name for b in backups)}")
    return path


# --------------------------------------------------------------------------
# Verification
# --------------------------------------------------------------------------
def check_integrity(path: Path) -> tuple[bool, str]:
    """Deeper check than a checksum: is the archive itself readable?"""
    name = path.name
    try:
        if name.endswith(".sql.gz"):
            total = 0
            with gzip.open(path, "rb") as fh:
                while True:
                    block = fh.read(1024 * 1024)
                    if not block:
                        break
                    total += len(block)
            if total == 0:
                return False, "gzip stream is empty"
            return True, f"gzip OK ({human_size(total)} uncompressed)"
        if ".tar" in name:
            with tarfile.open(path) as tar:
                count = sum(1 for _ in tar)
            return True, f"tar OK ({count} entries)"
        if name.endswith(".json"):
            json.loads(path.read_text(encoding="utf-8"))
            return True, "JSON OK"
    except (OSError, EOFError, tarfile.TarError, json.JSONDecodeError, UnicodeDecodeError) as exc:
        return False, f"{type(exc).__name__}: {exc}"
    return True, "no structural check for this file type"


def verify_backup(backup_path: Path) -> dict:
    manifest = json.loads((backup_path / "manifest.json").read_text(encoding="utf-8"))
    results = []
    all_ok = True
    for entry in manifest["files"]:
        fpath = backup_path / entry["name"]
        if not fpath.exists():
            results.append({"name": entry["name"], "expected": entry["sha256"], "actual": "MISSING",
                            "checksum_ok": False, "integrity_ok": False, "detail": "file missing"})
            all_ok = False
            continue
        actual = sha256_file(fpath)
        checksum_ok = actual == entry["sha256"]
        integrity_ok, detail = check_integrity(fpath)
        if not (checksum_ok and integrity_ok):
            all_ok = False
        results.append({"name": entry["name"], "expected": entry["sha256"], "actual": actual,
                        "checksum_ok": checksum_ok, "integrity_ok": integrity_ok, "detail": detail})
    return {"backup_id": manifest["backup_id"], "site": manifest["site"],
            "status": "PASS" if all_ok else "FAIL", "files": results}


def report_verification(reports_dir: Path, result: dict) -> Path:
    rows = [[f["name"], "OK" if f["checksum_ok"] else "MISMATCH", f["expected"][:16] + "…",
             (f["actual"][:16] + "…") if f["actual"] != "MISSING" else "MISSING",
             ("OK" if f["integrity_ok"] else "FAILED") + f" — {f['detail']}"] for f in result["files"]]
    stamp = utc_now().strftime("%Y%m%dT%H%M%SZ")
    return write_report(
        reports_dir, f"verify_{result['backup_id']}_{stamp}.md", "Backup Verification Report",
        {"Backup ID": result["backup_id"], "Site": result["site"], "Verified at (UTC)": utc_now().isoformat(timespec="seconds")},
        ["File", "SHA-256", "Expected", "Actual", "Integrity"], rows, result["status"])


# --------------------------------------------------------------------------
# Commands
# --------------------------------------------------------------------------
def list_remote_names(runner: Runner, remote_dir: str) -> list[str]:
    out = runner.sh(f"ls -1 {shlex.quote(remote_dir)} 2>/dev/null || true")
    return [line.strip() for line in out.splitlines() if line.strip()]


def cmd_backup(args, runner: Runner) -> int:
    backup_dir = Path(args.backup_dir)
    reports_dir = Path(args.reports_dir)
    backup_dir.mkdir(parents=True, exist_ok=True)
    runner.ensure_running()

    remote_dir = f"{runner.bench_path}/sites/{args.site}/private/backups"
    before = set(list_remote_names(runner, remote_dir))

    cmd = f"bench --site {shlex.quote(args.site)} backup"
    if not args.db_only:
        cmd += " --with-files"
    log.info("Running: %s", cmd)
    runner.sh(cmd)

    after = list_remote_names(runner, remote_dir)
    groups: dict[str, list[str]] = {}
    for name in after:
        m = BACKUP_FILE_RE.match(name)
        # bench writes dots as underscores in file names (crm.localhost -> crm_localhost)
        if m and m.group("site") in (args.site, args.site.replace(".", "_")):
            groups.setdefault(m.group("ts"), []).append(name)
    if not groups:
        raise ToolError(f"Bench reported success but no backup files were found in {remote_dir}")
    backup_id = max(groups)
    names = sorted(groups[backup_id])
    if not any(n.endswith("database.sql.gz") for n in names):
        raise ToolError(f"Backup {backup_id} has no database dump: {names}")
    if set(names) <= before:
        log.warning("No new files appeared; using the most recent existing backup %s", backup_id)

    final_dir = backup_dir / backup_id
    if final_dir.exists():
        raise ToolError(f"Backup directory already exists: {final_dir}")
    tmp_dir = backup_dir / f".tmp-{backup_id}"
    if tmp_dir.exists():
        shutil.rmtree(tmp_dir)
    tmp_dir.mkdir()

    try:
        entries = []
        for name in names:
            remote_file = f"{remote_dir}/{name}"
            local_file = tmp_dir / name
            log.info("Copying %s", name)
            runner.copy_from(remote_file, local_file)
            local_hash = sha256_file(local_file)
            remote_hash = runner.remote_sha256(remote_file)
            if local_hash != remote_hash:
                raise ToolError(f"Copy corrupted for {name}: source {remote_hash} != copy {local_hash}")
            kind = BACKUP_FILE_RE.match(name).group("kind")
            entries.append({"name": name, "kind": kind, "size": local_file.stat().st_size, "sha256": local_hash})
            log.info("  %s  %s", local_hash[:16], human_size(local_file.stat().st_size))

        manifest = {"backup_id": backup_id, "site": args.site, "tool_version": __version__,
                    "created_utc": utc_now().isoformat(timespec="seconds"),
                    "with_files": not args.db_only, "files": entries}
        (tmp_dir / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
        tmp_dir.rename(final_dir)
    except Exception:
        shutil.rmtree(tmp_dir, ignore_errors=True)
        raise

    log.info("Backup stored in %s", final_dir)
    result = verify_backup(final_dir)
    report_verification(reports_dir, result)

    rows = [[e["name"], human_size(e["size"]), e["sha256"]] for e in entries]
    write_report(reports_dir, f"backup_{backup_id}.md", "Backup Report",
                 {"Backup ID": backup_id, "Site": args.site, "Created (UTC)": manifest["created_utc"],
                  "Location": str(final_dir), "Includes files": str(not args.db_only),
                  "Post-backup verification": result["status"]},
                 ["File", "Size", "SHA-256"], rows, "SUCCESS" if result["status"] == "PASS" else "FAILED")

    if result["status"] != "PASS":
        log.error("Post-backup verification FAILED for %s", backup_id)
        return EXIT_VERIFY_FAILED
    if not args.no_prune:
        prune_backups(backup_dir, args.site, args.keep, dry_run=False)
    return EXIT_OK


def cmd_verify(args, runner: Runner) -> int:
    backup_dir = Path(args.backup_dir)
    targets = list_backups(backup_dir, args.site) if args.all else [resolve_backup(backup_dir, args.site, args.backup_id)]
    if not targets:
        raise ToolError("No backups to verify.")
    exit_code = EXIT_OK
    for target in targets:
        result = verify_backup(target)
        report_verification(Path(args.reports_dir), result)
        log.info("Verification of %s: %s", target.name, result["status"])
        for f in result["files"]:
            if not (f["checksum_ok"] and f["integrity_ok"]):
                log.error("  %s: checksum_ok=%s integrity=%s", f["name"], f["checksum_ok"], f["detail"])
        if result["status"] != "PASS":
            exit_code = EXIT_VERIFY_FAILED
    return exit_code


def prune_backups(backup_dir: Path, site: str, keep: int, dry_run: bool) -> list[str]:
    if keep < 1:
        raise ToolError("--keep must be at least 1")
    backups = list_backups(backup_dir, site)
    doomed = backups[:-keep] if len(backups) > keep else []
    removed = []
    for d in doomed:
        if dry_run:
            log.info("[dry-run] would delete %s", d.name)
        else:
            shutil.rmtree(d)
            log.info("Retention: deleted old backup %s", d.name)
        removed.append(d.name)
    log.info("Retention policy: keep latest %d, %d present, %d %s", keep, len(backups), len(removed),
             "would be deleted" if dry_run else "deleted")
    return removed


def cmd_prune(args, runner: Runner) -> int:
    prune_backups(Path(args.backup_dir), args.site, args.keep, args.dry_run)
    return EXIT_OK


def cmd_list(args, runner: Runner) -> int:
    backups = list_backups(Path(args.backup_dir), args.site)
    if not backups:
        print("No backups found.")
        return EXIT_OK
    print(f"{'BACKUP ID':<18} {'CREATED (UTC)':<26} {'SIZE':>10}  FILES")
    for d in backups:
        m = json.loads((d / "manifest.json").read_text())
        total = sum(f["size"] for f in m["files"])
        print(f"{m['backup_id']:<18} {m['created_utc']:<26} {human_size(total):>10}  {len(m['files'])}")
    return EXIT_OK


def cmd_restore(args, runner: Runner) -> int:
    """Restore a backup into a SEPARATE test environment (never the source)."""
    if args.test_container == runner.container or (runner.container is None and not args.test_container):
        raise ToolError("Refusing to restore: the test container must differ from the source container.")
    password = os.environ.get(PASSWORD_ENV)
    if not password:
        raise ToolError(f"Set the {PASSWORD_ENV} environment variable (MariaDB root password of the TEST environment).")

    backup_path = resolve_backup(Path(args.backup_dir), args.site, args.backup_id)
    log.info("Pre-restore verification of %s", backup_path.name)
    result = verify_backup(backup_path)
    report_verification(Path(args.reports_dir), result)
    if result["status"] != "PASS":
        raise ToolError("Backup failed verification; refusing to restore a corrupt backup.")

    manifest = json.loads((backup_path / "manifest.json").read_text())
    test = Runner(args.test_container, args.test_bench_path)
    test.ensure_running()

    staging = f"{test.bench_path}/restore-staging/{manifest['backup_id']}"
    test.sh(f"mkdir -p {shlex.quote(staging)}")
    steps: list[list[str]] = []
    try:
        for entry in manifest["files"]:
            test.copy_to(backup_path / entry["name"], staging)
        by_kind = {e["kind"]: f"{staging}/{e['name']}" for e in manifest["files"]}
        sql = next(v for k, v in by_kind.items() if k == "database.sql.gz")
        cmd = f"bench --site {shlex.quote(args.test_site)} --force restore {shlex.quote(sql)}"
        for kind, flag in (("files.tar", "--with-public-files"), ("files.tar.gz", "--with-public-files"),
                           ("private-files.tar", "--with-private-files"), ("private-files.tar.gz", "--with-private-files")):
            if kind in by_kind:
                cmd += f" {flag} {shlex.quote(by_kind[kind])}"
        cmd += f' --db-root-password "${PASSWORD_ENV}"'
        log.info("Restoring into test site '%s' in %s", args.test_site, args.test_container)
        test.sh(cmd, pass_env=(PASSWORD_ENV,))
        steps.append(["bench restore", "OK"])
        test.sh(f"bench --site {shlex.quote(args.test_site)} clear-cache")
        steps.append(["clear-cache", "OK"])

        for doctype in ("CRM Lead", "CRM Deal"):
            try:
                # frappe.db.sql returns ((n,),), which is always truthy, so bench prints it even when n == 0
                query = f"select count(*) from `tab{doctype}`"
                out = test.sh(f"bench --site {shlex.quote(args.test_site)} execute frappe.db.sql "
                              f"--args {shlex.quote(json.dumps([query]))}").strip().splitlines()[-1]
                steps.append([f"record count: {doctype}", str(json.loads(out)[0][0])])
            except (ToolError, IndexError, ValueError, KeyError, TypeError) as exc:
                msg = (str(exc).splitlines() or [type(exc).__name__])[0]
                log.warning("Could not count %s: %s", doctype, msg)
                steps.append([f"record count: {doctype}", "unavailable"])
        status = "SUCCESS"
    finally:
        try:
            test.sh(f"rm -rf {shlex.quote(staging)}")
        except ToolError as exc:
            log.warning("Could not remove staging dir: %s", str(exc).splitlines()[0])

    write_report(Path(args.reports_dir), f"restore_{manifest['backup_id']}_{utc_now().strftime('%Y%m%dT%H%M%SZ')}.md",
                 "Restore Test Report",
                 {"Backup ID": manifest["backup_id"], "Source site": manifest["site"],
                  "Test container": args.test_container, "Test site": args.test_site,
                  "Restored at (UTC)": utc_now().isoformat(timespec="seconds")},
                 ["Step", "Result"], steps, status,
                 ["Backup was checksum-verified before restore.", "Source environment was not touched."])
    log.info("Restore finished. Open the test site to inspect it.")
    return EXIT_OK


# --------------------------------------------------------------------------
# CLI
# --------------------------------------------------------------------------
def setup_logging(log_file: Path, verbose: bool) -> None:
    for handler in list(log.handlers):
        handler.close()
        log.removeHandler(handler)
    log.setLevel(logging.DEBUG)
    fmt =logging.Formatter("%(asctime)s | %(levelname)-7s | %(message)s")
    console = logging.StreamHandler(sys.stderr)
    console.setLevel(logging.DEBUG if verbose else logging.INFO)
    console.setFormatter(fmt)
    log.addHandler(console)
    log_file.parent.mkdir(parents=True, exist_ok=True)
    fileh = RotatingFileHandler(log_file, maxBytes=1_000_000, backupCount=3, encoding="utf-8")
    fileh.setLevel(logging.DEBUG)
    fileh.setFormatter(fmt)
    log.addHandler(fileh)


def build_parser() -> argparse.ArgumentParser:
    env = os.environ.get
    p = argparse.ArgumentParser(prog="frappe_backup", description="Backup & restore automation for Frappe CRM.")
    p.add_argument("--site", default=env("FRAPPE_SITE", "crm.localhost"), help="site name (default: crm.localhost)")
    p.add_argument("--container", default=env("FRAPPE_CONTAINER", "crm-frappe-1"),
                   help="Docker container running bench (default: crm-frappe-1)")
    p.add_argument("--local", action="store_true", help="run bench on this machine instead of in a container")
    p.add_argument("--bench-path", default=env("FRAPPE_BENCH_PATH", "/home/frappe/frappe-bench"))
    p.add_argument("--backup-dir", default=env("BACKUP_DIR", "./backups"))
    p.add_argument("--reports-dir", default=env("REPORTS_DIR", "./reports"))
    p.add_argument("--log-file", default=env("BACKUP_LOG_FILE", "./logs/backup_tool.log"))
    p.add_argument("--keep", type=int, default=int(env("BACKUP_KEEP", "7")), help="backups to retain (default: 7)")
    p.add_argument("-v", "--verbose", action="store_true")
    p.add_argument("--version", action="version", version=__version__)
    sub = p.add_subparsers(dest="command", required=True)

    b = sub.add_parser("backup", help="create, copy, verify and prune a backup")
    b.add_argument("--db-only", action="store_true", help="skip public/private files")
    b.add_argument("--no-prune", action="store_true", help="skip the retention step")
    b.set_defaults(func=cmd_backup)

    v = sub.add_parser("verify", help="verify SHA-256 checksums and archive integrity")
    v.add_argument("backup_id", nargs="?", default="latest")
    v.add_argument("--all", action="store_true", help="verify every stored backup")
    v.set_defaults(func=cmd_verify)

    pr = sub.add_parser("prune", help="apply the retention policy")
    pr.add_argument("--dry-run", action="store_true")
    pr.set_defaults(func=cmd_prune)

    ls = sub.add_parser("list", help="list stored backups")
    ls.set_defaults(func=cmd_list)

    r = sub.add_parser("restore", help="restore a backup into a separate test environment")
    r.add_argument("backup_id", nargs="?", default="latest")
    r.add_argument("--test-container", required=True, help="container of the TEST bench (must differ from source)")
    r.add_argument("--test-site", default=env("TEST_SITE", "restore-test.localhost"))
    r.add_argument("--test-bench-path", default=env("TEST_BENCH_PATH", "/home/frappe/frappe-bench"))
    r.set_defaults(func=cmd_restore)
    return p


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    setup_logging(Path(args.log_file), args.verbose)
    runner = Runner(None if args.local else args.container, args.bench_path)
    try:
        return args.func(args, runner)
    except ToolError as exc:
        log.error("%s", exc)
        return EXIT_ERROR
    except KeyboardInterrupt:
        log.error("Interrupted.")
        return 130
    except Exception:  # last-resort handler: log the traceback, exit non-zero
        log.exception("Unexpected error")
        return EXIT_ERROR


if __name__ == "__main__":
    sys.exit(main())
