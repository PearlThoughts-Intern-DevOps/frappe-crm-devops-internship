
#!/usr/bin/env python3
"""Backup and restore tool for Frappe CRM running under Docker Compose.
 
Run on the Docker host (for example the EC2 instance). The tool talks to the
bench container with `docker compose exec` and only uses the Python standard
library.
 
Commands:
    backup    run `bench backup --with-files`, copy the files to the host,
              write a SHA-256 manifest, then apply retention
    verify    recompute SHA-256 hashes and compare them with the manifest
    restore   verify, then restore into a SEPARATE test site (never the source)
    cleanup   keep only the newest N backups
    list      show stored backups
"""
 
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
import time
from datetime import datetime
from pathlib import Path
 
BENCH_DIR = "/home/frappe/frappe-bench"
TS_RE = re.compile(r"^(\d{8}_\d{6})-")
TS_DIR_RE = re.compile(r"^\d{8}_\d{6}$")
REQUIRED_KINDS = ("database", "public_files", "private_files", "site_config")
# MariaDB 10.8 does not know this variable, but the dump written by the newer
# client inside the bench image contains it, which makes the restore fail.
INCOMPATIBLE_MARKER = b"NOTE_VERBOSITY"
 
log = logging.getLogger("frappe_backup")
 
# Secrets (passwords) that must never appear in logs or error messages.
_SECRETS = set()
 
 
def redact(text):
    for secret in _SECRETS:
        if secret:
            text = text.replace(secret, "***")
    return text
 
 
class ToolError(Exception):
    """A failure the tool understands and can report cleanly."""
 
 
# ----------------------------------------------------------------------------
# Small helpers
# ----------------------------------------------------------------------------
 
def file_kind(name):
    """Classify a bench backup file by its name."""
    if name.endswith("-database.sql.gz"):
        return "database"
    if name.endswith("-private-files.tar"):
        return "private_files"
    if name.endswith("-files.tar"):
        return "public_files"
    if name.endswith("-site_config_backup.json"):
        return "site_config"
    return None
 
 
def group_sets(names):
    """Group bench backup file names by timestamp: {ts: {kind: filename}}."""
    sets = {}
    for name in names:
        match = TS_RE.match(name)
        kind = file_kind(name)
        if match and kind:
            sets.setdefault(match.group(1), {})[kind] = name
    return sets
 
 
def sha256_file(path, chunk=1024 * 1024):
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for block in iter(lambda: handle.read(chunk), b""):
            digest.update(block)
    return digest.hexdigest()
 
 
def now_str():
    return datetime.now().strftime("%Y%m%d_%H%M%S")
 
 
def run(cmd, cwd=None, timeout=1800):
    """Run a command, log it, and raise ToolError if it fails."""
    log.debug("run: %s", redact(" ".join(cmd)))
    try:
        proc = subprocess.run(
            cmd, cwd=cwd, capture_output=True, text=True, timeout=timeout
        )
    except FileNotFoundError:
        raise ToolError(f"command not found: {cmd[0]} (is Docker installed?)")
    except subprocess.TimeoutExpired:
        raise ToolError(f"command timed out after {timeout}s: {' '.join(cmd[:6])}")
    if proc.returncode != 0:
        tail = (proc.stdout + proc.stderr).strip().splitlines()[-15:]
        raise ToolError(
            redact(
                f"command failed (exit {proc.returncode}): {' '.join(cmd[:8])}\n"
                + "\n".join(tail)
            )
        )
    return proc
 
 
class Config:
    def __init__(self, args):
        self.compose_dir = Path(args.compose_dir).expanduser()
        self.root = Path(args.backup_root).expanduser()
        self.site = args.site
        self.service = args.service
        self.backups_dir = self.root / "backups"
        self.reports_dir = self.root / "reports"
        self.logs_dir = self.root / "logs"
        self.container_backups = f"{BENCH_DIR}/sites/{self.site}/private/backups"
 
    def make_dirs(self):
        for folder in (self.backups_dir, self.reports_dir, self.logs_dir):
            folder.mkdir(parents=True, exist_ok=True)
 
 
def container_sh(cfg, script):
    """Run a shell snippet inside the bench container."""
    cmd = ["docker", "compose", "exec", "-T", cfg.service, "bash", "-c", script]
    return run(cmd, cwd=cfg.compose_dir)
 
 
def bench(cfg, bench_args):
    """Run a bench command inside the bench container."""
    return container_sh(cfg, f"cd {BENCH_DIR} && bench {bench_args}")
 
 
def copy_from_container(cfg, container_path, host_path):
    run(
        ["docker", "compose", "cp", f"{cfg.service}:{container_path}", str(host_path)],
        cwd=cfg.compose_dir,
    )
 
 
def copy_to_container(cfg, host_path, container_path):
    run(
        ["docker", "compose", "cp", str(host_path), f"{cfg.service}:{container_path}"],
        cwd=cfg.compose_dir,
    )
 
 
def write_report(cfg, name, data):
    cfg.make_dirs()
    path = cfg.reports_dir / f"{name}_{now_str()}.json"
    path.write_text(json.dumps(data, indent=2) + "\n")
    log.info("report written: %s", path)
    return path
 
 
def list_container_sets(cfg):
    # The folder may not exist before the very first backup of a site.
    out = container_sh(cfg, f"ls -1 {cfg.container_backups} 2>/dev/null || true").stdout
    return group_sets(out.split())
 
 
def stored_timestamps(cfg):
    """Backups on the host that have a manifest, oldest first."""
    if not cfg.backups_dir.is_dir():
        return []
    return sorted(
        p.name
        for p in cfg.backups_dir.iterdir()
        if p.is_dir() and TS_DIR_RE.match(p.name) and (p / "manifest.json").is_file()
    )
 
 
# ----------------------------------------------------------------------------
# Commands
# ----------------------------------------------------------------------------
 
def cmd_backup(cfg, args):
    cfg.make_dirs()
    started = time.time()
    before = set(list_container_sets(cfg))
 
    log.info("running bench backup for %s", cfg.site)
    result = bench(cfg, f"--site {shlex.quote(cfg.site)} backup --with-files")
 
    after = list_container_sets(cfg)
    new = sorted(set(after) - before)
    if new:
        ts = new[-1]
    elif after:
        ts = max(after)
        log.warning("no new backup set detected; using the newest one (%s)", ts)
    else:
        raise ToolError("bench reported success but no backup files were found")
 
    files = after[ts]
    missing = [k for k in REQUIRED_KINDS if k not in files]
    if missing:
        raise ToolError(f"backup {ts} is incomplete, missing: {', '.join(missing)}")
 
    dest = cfg.backups_dir / ts
    dest.mkdir(parents=True, exist_ok=True)
    for name in files.values():
        log.info("copying %s to host", name)
        copy_from_container(cfg, f"{cfg.container_backups}/{name}", dest / name)
 
    manifest = {
        "timestamp": ts,
        "site": cfg.site,
        "created_at": datetime.now().isoformat(timespec="seconds"),
        "files": {},
    }
    for kind, name in sorted(files.items()):
        path = dest / name
        manifest["files"][name] = {
            "kind": kind,
            "size_bytes": path.stat().st_size,
            "sha256": sha256_file(path),
        }
        log.info("sha256 %s  %s", manifest["files"][name]["sha256"], name)
    (dest / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
 
    write_report(
        cfg,
        f"backup_{ts}",
        {
            "result": "success",
            "timestamp": ts,
            "site": cfg.site,
            "duration_seconds": round(time.time() - started, 1),
            "files": manifest["files"],
            "bench_output_tail": result.stdout.strip().splitlines()[-6:],
        },
    )
 
    if not args.no_cleanup:
        prune(cfg, args.keep)
    log.info("backup %s complete", ts)
    return 0
 
 
def verify_backup(cfg, ts):
    """Compare files on disk with the manifest. Returns (ok, report_dict)."""
    folder = cfg.backups_dir / ts
    manifest_path = folder / "manifest.json"
    if not manifest_path.is_file():
        raise ToolError(f"no manifest for backup {ts} at {manifest_path}")
    try:
        manifest = json.loads(manifest_path.read_text())
    except json.JSONDecodeError as exc:
        raise ToolError(f"manifest for {ts} is not valid JSON: {exc}")
 
    checks, ok = [], True
    for name, meta in manifest["files"].items():
        path = folder / name
        if not path.is_file():
            status, actual = "missing", None
        else:
            actual = sha256_file(path)
            status = "ok" if actual == meta["sha256"] else "mismatch"
        if status != "ok":
            ok = False
        checks.append(
            {"file": name, "status": status, "expected": meta["sha256"], "actual": actual}
        )
        log.info("verify %-9s %s", status.upper(), name)
 
    report = {
        "timestamp": ts,
        "site": manifest.get("site"),
        "result": "pass" if ok else "fail",
        "checks": checks,
    }
    return ok, report
 
 
def resolve_timestamp(cfg, requested):
    if requested:
        return requested
    stamps = stored_timestamps(cfg)
    if not stamps:
        raise ToolError(f"no backups found in {cfg.backups_dir}")
    return stamps[-1]
 
 
def cmd_verify(cfg, args):
    ts = resolve_timestamp(cfg, args.timestamp)
    ok, report = verify_backup(cfg, ts)
    write_report(cfg, f"verify_{ts}", report)
    if ok:
        log.info("backup %s verified: all checksums match", ts)
        return 0
    log.error("backup %s FAILED verification", ts)
    return 2
 
 
def prune(cfg, keep):
    if keep < 1:
        raise ToolError("--keep must be at least 1")
    stamps = stored_timestamps(cfg)
    old = stamps[:-keep] if len(stamps) > keep else []
    for ts in old:
        shutil.rmtree(cfg.backups_dir / ts)
        log.info("retention: removed old backup %s", ts)
    log.info("retention: %d backup(s) kept (limit %d)", len(stamps) - len(old), keep)
    return old
 
 
def cmd_cleanup(cfg, args):
    prune(cfg, args.keep)
    return 0
 
 
def cmd_list(cfg, args):
    stamps = stored_timestamps(cfg)
    if not stamps:
        print(f"no backups in {cfg.backups_dir}")
        return 0
    for ts in stamps:
        manifest = json.loads((cfg.backups_dir / ts / "manifest.json").read_text())
        size = sum(f["size_bytes"] for f in manifest["files"].values())
        print(f"{ts}  site={manifest['site']}  files={len(manifest['files'])}  bytes={size}")
    return 0
 
 
def sanitize_dump(src, dst):
    """Copy a .sql.gz file, dropping lines the older MariaDB server rejects."""
    removed = 0
    with gzip.open(src, "rb") as fin, gzip.open(dst, "wb") as fout:
        for line in fin:
            if INCOMPATIBLE_MARKER in line:
                removed += 1
                continue
            fout.write(line)
    return removed
 
 
def cmd_restore(cfg, args):
    cfg.make_dirs()
    target = args.target
    if target == cfg.site:
        raise ToolError(
            f"refusing to restore over the source site '{cfg.site}'; "
            "choose a separate test site with --target"
        )
    password = args.db_root_password or os.environ.get("DB_ROOT_PASSWORD")
    if not password:
        raise ToolError("MariaDB root password missing: use --db-root-password or set DB_ROOT_PASSWORD")
 
    _SECRETS.add(password)
    if len(args.admin_password) >= 6:  # avoid garbling words with the short default
        _SECRETS.add(args.admin_password)
    ts = resolve_timestamp(cfg, args.timestamp)
    log.info("restoring backup %s into test site %s", ts, target)
 
    ok, vreport = verify_backup(cfg, ts)
    write_report(cfg, f"verify_{ts}", vreport)
    if not ok:
        raise ToolError(f"backup {ts} failed checksum verification; restore aborted")
 
    folder = cfg.backups_dir / ts
    manifest = json.loads((folder / "manifest.json").read_text())
    by_kind = {meta["kind"]: name for name, meta in manifest["files"].items()}
    for kind in ("database", "public_files", "private_files"):
        if kind not in by_kind:
            raise ToolError(f"backup {ts} has no {kind} file")
 
    steps = []
    q_target, q_pw = shlex.quote(target), shlex.quote(password)
 
    exists = run(
        ["docker", "compose", "exec", "-T", cfg.service, "bash", "-c",
         f"test -d {BENCH_DIR}/sites/{q_target} && echo yes || echo no"],
        cwd=cfg.compose_dir,
    ).stdout.strip()
    if exists != "yes":
        log.info("test site %s does not exist, creating it", target)
        bench(
            cfg,
            f"new-site {q_target} --mariadb-root-password {q_pw} "
            f"--admin-password {shlex.quote(args.admin_password)} "
            "--mariadb-user-host-login-scope='%'",
        )
        steps.append("created test site")
    else:
        steps.append("test site already existed")
 
    db_name = by_kind["database"]
    db_path = folder / db_name
    staged_db = db_path
    removed = 0
    if not args.no_sanitize:
        staged_db = cfg.root / f"cleaned_{db_name}"
        removed = sanitize_dump(db_path, staged_db)
        log.info("compat step: removed %d incompatible line(s) from a temporary copy", removed)
        steps.append(f"removed {removed} incompatible dump line(s) from a temporary copy")
 
    stage = f"/tmp/restore/{ts}"
    container_sh(cfg, f"rm -rf {stage} && mkdir -p {stage}")
    try:
        copy_to_container(cfg, staged_db, f"{stage}/{db_name}")
        for kind in ("public_files", "private_files"):
            copy_to_container(cfg, folder / by_kind[kind], f"{stage}/{by_kind[kind]}")
        steps.append("staged files in container")
 
        log.info("running bench restore")
        bench(
            cfg,
            f"--site {q_target} --force restore {stage}/{db_name} "
            f"--with-public-files {stage}/{by_kind['public_files']} "
            f"--with-private-files {stage}/{by_kind['private_files']} "
            f"--mariadb-root-password {q_pw}",
        )
        steps.append("bench restore completed")
 
        apps = bench(cfg, f"--site {q_target} list-apps").stdout.strip()
        log.info("apps on %s:\n%s", target, apps)
        if not re.search(r"^crm\b", apps, re.MULTILINE):
            raise ToolError(f"restore finished but 'crm' app not found on {target}")
        steps.append("verified crm app present on test site")
    finally:
        try:
            container_sh(cfg, f"rm -rf {stage}")
        except ToolError as exc:
            log.warning("could not clean up %s: %s", stage, exc)
        if staged_db != db_path and Path(staged_db).exists():
            Path(staged_db).unlink()
 
    write_report(
        cfg,
        f"restore_{ts}",
        {
            "result": "success",
            "timestamp": ts,
            "source_site": cfg.site,
            "target_site": target,
            "steps": steps,
            "apps_on_target": apps.splitlines(),
        },
    )
    log.info("restore of %s into %s complete", ts, target)
    return 0
 
 
# ----------------------------------------------------------------------------
# CLI
# ----------------------------------------------------------------------------
 
def build_parser():
    parser = argparse.ArgumentParser(
        description="Backup and restore tool for Frappe CRM (Docker Compose)"
    )
    parser.add_argument(
        "--compose-dir",
        default=os.environ.get(
            "FRAPPE_COMPOSE_DIR", "~/frappe-crm-devops-internship/docker"
        ),
        help="folder containing docker-compose.yml",
    )
    parser.add_argument(
        "--backup-root",
        default=os.environ.get("FRAPPE_BACKUP_ROOT", "~/frappe-backups"),
        help="where backups, reports and logs are stored on the host",
    )
    parser.add_argument("--site", default="crm.localhost", help="source site name")
    parser.add_argument("--service", default="frappe", help="compose service name")
    parser.add_argument("-v", "--verbose", action="store_true", help="debug logging")
 
    sub = parser.add_subparsers(dest="command", required=True)
 
    p = sub.add_parser("backup", help="create, copy, checksum and prune a backup")
    p.add_argument("--keep", type=int, default=7, help="backups to retain (default 7)")
    p.add_argument("--no-cleanup", action="store_true", help="skip retention")
    p.set_defaults(func=cmd_backup)
 
    p = sub.add_parser("verify", help="verify SHA-256 checksums")
    p.add_argument("--timestamp", help="backup timestamp (default: latest)")
    p.set_defaults(func=cmd_verify)
 
    p = sub.add_parser("restore", help="restore into a separate test site")
    p.add_argument("--timestamp", help="backup timestamp (default: latest)")
    p.add_argument("--target", default="test.localhost", help="test site name")
    p.add_argument("--db-root-password", help="MariaDB root password (or env DB_ROOT_PASSWORD)")
    p.add_argument("--admin-password", default="admin", help="Administrator password for a new test site")
    p.add_argument("--no-sanitize", action="store_true", help="do not strip incompatible dump lines")
    p.set_defaults(func=cmd_restore)
 
    p = sub.add_parser("cleanup", help="keep only the newest N backups")
    p.add_argument("--keep", type=int, default=7)
    p.set_defaults(func=cmd_cleanup)
 
    p = sub.add_parser("list", help="list stored backups")
    p.set_defaults(func=cmd_list)
 
    return parser
 
 
def setup_logging(cfg, verbose):
    cfg.make_dirs()
    log.setLevel(logging.DEBUG)
    fmt = logging.Formatter("%(asctime)s %(levelname)-7s %(message)s")
    console = logging.StreamHandler()
    console.setLevel(logging.DEBUG if verbose else logging.INFO)
    console.setFormatter(fmt)
    logfile = logging.FileHandler(cfg.logs_dir / "backup_tool.log")
    logfile.setLevel(logging.DEBUG)
    logfile.setFormatter(fmt)
    log.addHandler(console)
    log.addHandler(logfile)
 
 
def main(argv=None):
    args = build_parser().parse_args(argv)
    cfg = Config(args)
    setup_logging(cfg, args.verbose)
    try:
        if not cfg.compose_dir.is_dir():
            raise ToolError(f"compose directory not found: {cfg.compose_dir}")
        return args.func(cfg, args)
    except ToolError as exc:
        log.error("%s", exc)
        return 1
    except KeyboardInterrupt:
        log.error("interrupted")
        return 130
 
 
if __name__ == "__main__":
    sys.exit(main())