"""Command-Line Interface (CLI) router for Frappe Backup Manager."""

import argparse
import logging
from pathlib import Path
import sys

from .config import BackupConfig
from .exception import BackupManagerError, VerificationError
from .lock import process_lock
from .logger import setup_logger
from .models import BackupSet, discover_backup_sets
from .restore import RestoreManager
from .retention import RetentionPolicy
from .runner import BenchRunner
from .verifier import IntegrityVerifier


def _select_backup_set(
    config: BackupConfig, timestamp: str | None = None
) -> BackupSet:
    """Finds a specific backup set by timestamp or returns the newest complete set."""
    sets = discover_backup_sets(config.backup_dir, config.site, config.site_slug)
    if not sets:
        raise BackupManagerError(
            f"No backup sets found for site '{config.site}' in {config.backup_dir}"
        )

    if timestamp:
        for bset in sets:
            if bset.timestamp == timestamp:
                return bset
        raise BackupManagerError(
            f"Backup set with timestamp '{timestamp}' not found for site '{config.site}'."
        )

    complete = [s for s in sets if s.is_complete]
    if not complete:
        raise BackupManagerError(
            f"No complete backup sets found for site '{config.site}'."
        )
    return complete[0]


def cmd_backup(args: argparse.Namespace, config: BackupConfig) -> int:
    """Executes bench backup, generates SHA-256 manifests, and enforces retention."""
    logger = logging.getLogger(__name__)
    runner = BenchRunner(config)
    verifier = IntegrityVerifier()
    retention = RetentionPolicy(config)

    with process_lock():
        logger.info("Triggering Frappe backup (--with-files) for site '%s'...", config.site)
        runner.execute(["--site", config.site, "backup", "--with-files"])

        latest_set = _select_backup_set(config)
        logger.info("Located newly created backup set: %s", latest_set.timestamp)

        verifier.generate_manifests(latest_set, config.site_slug)

        if args.verify:
            logger.info("Running post-backup verification check...")
            verifier.verify_backup_set(latest_set)

        # Safety rule: Only prune after the current backup + verification succeeds
        retention.enforce(retention_count=config.retention_count)
        logger.info("Backup workflow completed successfully for set %s.", latest_set.timestamp)
    return 0


def cmd_verify(args: argparse.Namespace, config: BackupConfig) -> int:
    """Verifies SHA-256 digests and archive headers for a target backup set."""
    logger = logging.getLogger(__name__)
    verifier = IntegrityVerifier()

    target_set = _select_backup_set(config, timestamp=args.timestamp)
    logger.info("Verifying backup set %s for site '%s'...", target_set.timestamp, config.site)

    if not target_set.manifest:
        raise VerificationError(
            f"Backup set {target_set.timestamp} has no manifest.json. Run 'backup' or generate manifests first."
        )

    verifier.verify_backup_set(target_set)
    logger.info("Verification PASSED: All 4 artifacts in set %s are intact.", target_set.timestamp)
    return 0


def cmd_restore(args: argparse.Namespace, config: BackupConfig) -> int:
    """Restores a verified backup set into the isolated test site."""
    runner = BenchRunner(config)
    verifier = IntegrityVerifier()
    restore_mgr = RestoreManager(config, runner, verifier)

    with process_lock():
        target_set = _select_backup_set(config, timestamp=args.timestamp)
        restore_mgr.restore(target_set, test_site=config.test_site)
    return 0


def cmd_list(args: argparse.Namespace, config: BackupConfig) -> int:
    """Lists all discovered backup sets in a clean tabular summary."""
    sets = discover_backup_sets(config.backup_dir, config.site, config.site_slug)
    if not sets:
        print(f"No backup sets found for site '{config.site}' in {config.backup_dir}")
        return 0

    header = f"{'INDEX':<6} {'TIMESTAMP':<17} {'COMPLETE':<10} {'VERIFIED':<10} {'SIZE (KiB)':<12} {'RETENTION STATUS'}"
    print(header)
    print("-" * len(header))

    complete_idx = 0
    for bset in sets:
        if bset.is_complete:
            complete_idx += 1
            ret_status = (
                f"KEEP ({complete_idx}/{config.retention_count})"
                if complete_idx <= config.retention_count
                else "ELIGIBLE FOR PRUNE"
            )
        else:
            ret_status = "INCOMPLETE (ORPHAN)"

        size_kib = f"{bset.total_size_bytes / 1024.0:.1f}"
        print(
            f"{complete_idx if bset.is_complete else '-':<6} "
            f"{bset.timestamp:<17} "
            f"{'YES' if bset.is_complete else 'NO':<10} "
            f"{'YES' if bset.is_verified else 'NO':<10} "
            f"{size_kib:<12} "
            f"{ret_status}"
        )
    return 0


def cmd_prune(args: argparse.Namespace, config: BackupConfig) -> int:
    """Manually triggers the rolling retention policy."""
    retention = RetentionPolicy(config)
    with process_lock():
        retention.enforce(retention_count=config.retention_count, dry_run=args.dry_run)
    return 0


def build_parser() -> argparse.ArgumentParser:
    """Constructs the CLI argument parser and subcommands."""
    parser = argparse.ArgumentParser(
        prog="backup_manager.py",
        description="Frappe CRM Backup Automation, SHA-256 Verification & Disaster Recovery CLI.",
    )
    parser.add_argument(
        "--bench-path",
        type=Path,
        default=None,
        help="Path to frappe-bench root directory (auto-detected by default).",
    )
    parser.add_argument(
        "--container",
        type=str,
        default=None,
        help="Docker container name if executing from host (default: crm-frappe-1).",
    )
    parser.add_argument(
        "-v", "--verbose", action="store_true", help="Enable debug-level console logging."
    )

    subparsers = parser.add_subparsers(dest="subcommand", required=True)

    # 1. backup
    p_backup = subparsers.add_parser("backup", help="Run backup, generate SHA-256 manifest, and prune old sets.")
    p_backup.add_argument("--site", default="crm.localhost", help="Source Frappe site name.")
    p_backup.add_argument("--retention", type=int, default=7, help="Number of latest backup sets to keep.")
    p_backup.add_argument("--verify", action="store_true", default=True, help="Verify SHA-256 immediately after backup.")

    # 2. verify
    p_verify = subparsers.add_parser("verify", help="Verify SHA-256 checksums and archive headers.")
    p_verify.add_argument("--site", default="crm.localhost", help="Source Frappe site name.")
    p_verify.add_argument("--timestamp", default=None, help="Specific backup timestamp (YYYYMMDD_HHMMSS). Defaults to latest.")

    # 3. restore
    p_restore = subparsers.add_parser("restore", help="Restore a verified backup into an isolated test site.")
    p_restore.add_argument("--site", default="crm.localhost", help="Source production site name.")
    p_restore.add_argument("--test-site", default="crm-test.localhost", help="Target isolated test site name.")
    p_restore.add_argument("--timestamp", default=None, help="Specific backup timestamp to restore. Defaults to latest.")
    p_restore.add_argument("--db-root-password", default=None, help="MariaDB root password (or set FRAPPE_DB_ROOT_PASSWORD).")

    # 4. list
    p_list = subparsers.add_parser("list", help="List discovered backup sets and their verification status.")
    p_list.add_argument("--site", default="crm.localhost", help="Source Frappe site name.")
    p_list.add_argument("--retention", type=int, default=7, help="Retention count threshold for display.")

    # 5. prune
    p_prune = subparsers.add_parser("prune", help="Prune backup sets older than the retention count.")
    p_prune.add_argument("--site", default="crm.localhost", help="Source Frappe site name.")
    p_prune.add_argument("--retention", type=int, default=7, help="Number of latest backup sets to keep.")
    p_prune.add_argument("--dry-run", action="store_true", help="Preview files to be deleted without removing them.")

    return parser


def main(argv: list[str] | None = None) -> int:
    """Main CLI entry point."""
    parser = build_parser()
    args = parser.parse_args(argv)

    cfg_kwargs: dict = {"site": getattr(args, "site", "crm.localhost"), "verbose": args.verbose}
    if args.bench_path is not None:
        cfg_kwargs["bench_path"] = args.bench_path
    if args.container is not None:
        cfg_kwargs["container_name"] = args.container
    if hasattr(args, "retention") and args.retention is not None:
        cfg_kwargs["retention_count"] = args.retention
    if hasattr(args, "test_site") and args.test_site is not None:
        cfg_kwargs["test_site"] = args.test_site
    if hasattr(args, "db_root_password") and args.db_root_password is not None:
        cfg_kwargs["db_root_password"] = args.db_root_password

    try:
        config = BackupConfig(**cfg_kwargs)
    except ValueError as exc:
        print(f"Configuration Error: {exc}", file=sys.stderr)
        return 1

    logger = setup_logger(config.log_file, verbose=config.verbose)

    dispatch = {
        "backup": cmd_backup,
        "verify": cmd_verify,
        "restore": cmd_restore,
        "list": cmd_list,
        "prune": cmd_prune,
    }

    try:
        return dispatch[args.subcommand](args, config)
    except BackupManagerError as exc:
        logger.error("%s: %s", exc.__class__.__name__, exc)
        return exc.exit_code
    except KeyboardInterrupt:
        logger.warning("Operation cancelled by user.")
        return 130
    except Exception as exc:
        logger.exception("Unexpected fatal error: %s", exc)
        return 1