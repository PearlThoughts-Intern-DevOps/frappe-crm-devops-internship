"""Isolated disaster recovery and test-site restoration orchestrator."""

import gzip
import json
import logging
from pathlib import Path
import re

from .config import BackupConfig
from .exception import BenchCommandError, RestoreError, VerificationError
from .models import BackupSet
from .runner import BenchRunner
from .verifier import IntegrityVerifier

logger = logging.getLogger(__name__)


class RestoreManager:
    """Orchestrates verified restoration into an isolated test site."""

    def __init__(
        self,
        config: BackupConfig,
        runner: BenchRunner,
        verifier: IntegrityVerifier,
    ):
        self.config = config
        self.runner = runner
        self.verifier = verifier

    def _to_bench_path(self, host_path: Path) -> str:
        """
        Translates a host filesystem Path into a path relative to the bench root
        (or container bench path) so 'bench restore' works in both Native and Docker modes.
        """
        try:
            rel_path = host_path.resolve().relative_to(self.config.bench_path.resolve())
        except ValueError:
            return str(host_path)

        if self.runner.is_native:
            return str(self.config.bench_path / rel_path)
        return str(self.config.container_bench_path / rel_path)

    def _prepare_database_archive(self, db_path: Path) -> tuple[Path, bool]:
        """
        Sanitizes MariaDB 11.x client 'NOTE_VERBOSITY' conditional comments
        (header line ~23 and footer line ~20148) for compatibility with MariaDB 10.8 servers.
        Returns (prepared_path, was_sanitized).
        """
        try:
            with gzip.open(db_path, "rb") as in_f:
                header = b"".join(in_f.readline() for _ in range(50))
                if b"NOTE_VERBOSITY" not in header:
                    return db_path, False

            logger.info(
                "Detected MariaDB NOTE_VERBOSITY conditional comments in %s. Sanitizing for restore...",
                db_path.name,
            )
            # Write to same volume-mounted directory (dot-prefixed) so both Host and Container see it
            # and discover_backup_sets() regex ignores it.
            sanitized_path = db_path.parent / f".sanitized_{db_path.name}"
            with (
                gzip.open(db_path, "rb") as src,
                gzip.open(sanitized_path, "wb", compresslevel=1) as dst,
            ):
                for line in src:
                    if b"NOTE_VERBOSITY" not in line:
                        dst.write(line)

            return sanitized_path, True
        except OSError as exc:
            logger.warning("Could not pre-check/sanitize database archive: %s", exc)
            return db_path, False

    def _ensure_test_site_exists(self, test_site: str) -> None:
        """Checks if the target test site exists; bootstraps it via 'bench new-site' if missing."""
        test_site_dir = self.config.sites_dir / test_site
        if (test_site_dir / "site_config.json").is_file():
            logger.info("Target test site '%s' already exists.", test_site)
            return

        logger.info("Test site '%s' not found. Bootstrapping new site...", test_site)
        try:
            self.runner.execute(
                [
                    "new-site",
                    test_site,
                    "--mariadb-root-password",
                    self.config.db_root_password,
                    "--admin-password",
                    self.config.admin_password,
                    "--no-mariadb-socket",
                ],
                timeout=900,
            )
            logger.info("Successfully created test site '%s'.", test_site)
        except BenchCommandError as exc:
            raise RestoreError(f"Failed to bootstrap test site '{test_site}': {exc}") from exc

    def _sync_encryption_key(self, backup_set: BackupSet, test_site: str) -> None:
        """Copies encryption_key from the backup config into the test site's site_config.json."""
        assert backup_set.site_config is not None
        target_config_path = self.config.sites_dir / test_site / "site_config.json"

        if not target_config_path.is_file():
            logger.warning("Could not locate %s to sync encryption_key.", target_config_path)
            return

        try:
            source_cfg = json.loads(backup_set.site_config.read_text(encoding="utf-8"))
            target_cfg = json.loads(target_config_path.read_text(encoding="utf-8"))

            enc_key = source_cfg.get("encryption_key")
            if enc_key and target_cfg.get("encryption_key") != enc_key:
                target_cfg["encryption_key"] = enc_key
                target_config_path.write_text(
                    json.dumps(target_cfg, indent=1) + "\n", encoding="utf-8"
                )
                logger.info("Synced encryption_key from backup set to '%s'.", test_site)
        except (OSError, json.JSONDecodeError) as exc:
            logger.warning("Failed to sync encryption_key to '%s': %s", test_site, exc)

    def _run_smoke_test(self, test_site: str) -> int:
        """Executes a Frappe ORM query against the restored database to verify health."""
        logger.info("Running post-restore ORM smoke test on '%s'...", test_site)
        try:
            # Clear cache so restored DB schema matches Redis state
            self.runner.execute(["--site", test_site, "clear-cache"], timeout=120)

            # Query User count via Frappe ORM
            res = self.runner.execute(
                ["--site", test_site, "execute", "frappe.db.count", "--args", "['User']"],
                timeout=120,
            )
            output = res.stdout.strip()
            match = re.search(r"(\d+)\s*$", output)
            if not match:
                raise RestoreError(
                    f"Smoke test returned unexpected output on '{test_site}': {output}"
                )
            user_count = int(match.group(1))
            if user_count < 1:
                raise RestoreError(
                    f"Smoke test failed: Restored database has {user_count} User records."
                )
            logger.info(
                "Smoke test PASSED: Restored site '%s' is responsive (%d User records verified).",
                test_site,
                user_count,
            )
            return user_count
        except BenchCommandError as exc:
            raise RestoreError(f"Post-restore smoke test failed on '{test_site}': {exc}") from exc

    def restore(self, backup_set: BackupSet, test_site: str | None = None) -> None:
        """
        1. Validates SHA-256 and archive structure of `backup_set`.
        2. Bootstraps `test_site` if it does not exist.
        3. Sanitizes MariaDB 11.x 'NOTE_VERBOSITY' directives if present.
        4. Restores database, public files, and private files.
        5. Disables background scheduler on `test_site` to prevent outbound leaks.
        6. Syncs `encryption_key` and executes post-restore ORM smoke test.
        """
        target_site = test_site or self.config.test_site
        if target_site == self.config.site:
            raise RestoreError(
                f"Safety violation: Refusing to restore over active production site '{self.config.site}'."
            )

        logger.info(
            "Starting pre-restore integrity verification for backup set %s...",
            backup_set.timestamp,
        )
        try:
            if backup_set.manifest and backup_set.manifest.is_file():
                self.verifier.verify_backup_set(backup_set)
            else:
                logger.warning(
                    "No manifest.json found for %s; running structural validation only.",
                    backup_set.timestamp,
                )
                self.verifier.validate_structure(backup_set)
        except VerificationError as exc:
            raise RestoreError(
                f"Aborting restore! Backup set {backup_set.timestamp} failed verification: {exc}"
            ) from exc

        self._ensure_test_site_exists(target_site)

        assert backup_set.database is not None
        assert backup_set.public_files is not None
        assert backup_set.private_files is not None

        # Prepare database (sanitizes NOTE_VERBOSITY if present)
        clean_db_path, is_temp = self._prepare_database_archive(backup_set.database)
        try:
            db_arg = self._to_bench_path(clean_db_path)
            pub_arg = self._to_bench_path(backup_set.public_files)
            priv_arg = self._to_bench_path(backup_set.private_files)

            logger.info(
                "Restoring backup set %s into isolated site '%s'...",
                backup_set.timestamp,
                target_site,
            )
            try:
                self.runner.execute(
                    [
                        "--site",
                        target_site,
                        "restore",
                        db_arg,
                        "--with-public-files",
                        pub_arg,
                        "--with-private-files",
                        priv_arg,
                        "--mariadb-root-password",
                        self.config.db_root_password,
                        "--force",
                    ],
                    timeout=1200,
                )
            except BenchCommandError as exc:
                raise RestoreError(
                    f"Bench restore failed on '{target_site}': {exc}"
                ) from exc
        finally:
            if is_temp:
                clean_db_path.unlink(missing_ok=True)
                logger.debug("Cleaned up temporary sanitized dump: %s", clean_db_path.name)

        # Safety Step: Disable background scheduler on test site immediately
        try:
            self.runner.execute(["--site", target_site, "scheduler", "disable"], timeout=60)
            logger.info("Disabled background scheduler on test site '%s' (safety isolation).", target_site)
        except BenchCommandError as exc:
            logger.warning("Could not disable scheduler on '%s': %s", target_site, exc)

        self._sync_encryption_key(backup_set, target_site)
        self._run_smoke_test(target_site)
        logger.info("Disaster recovery restoration into '%s' completed successfully.", target_site)