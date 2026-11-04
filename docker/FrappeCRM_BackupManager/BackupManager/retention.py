"""Rolling retention policy enforcement for Frappe Backup Sets."""

import logging

from .config import BackupConfig
from .models import BackupSet, discover_backup_sets

logger = logging.getLogger(__name__)


class RetentionPolicy:
    """Enforces the rolling 'keep latest N' retention rule across atomic backup sets."""

    def __init__(self, config: BackupConfig):
        self.config = config

    def enforce(
        self, retention_count: int | None = None, dry_run: bool = False
    ) -> list[BackupSet]:
        """
        Retains the newest `retention_count` complete backup sets and deletes older sets.
        Returns the list of pruned BackupSets.
        """
        keep_limit = retention_count if retention_count is not None else self.config.retention_count
        all_sets = discover_backup_sets(
            self.config.backup_dir, self.config.site, self.config.site_slug
        )

        # Only count complete backup sets toward the retention window
        complete_sets = [s for s in all_sets if s.is_complete]
        incomplete_sets = [s for s in all_sets if not s.is_complete]

        if incomplete_sets:
            logger.warning(
                "Found %d incomplete backup set(s): %s",
                len(incomplete_sets),
                ", ".join(s.timestamp for s in incomplete_sets),
            )

        if len(complete_sets) <= keep_limit:
            logger.info(
                "Retention check: %d complete set(s) found (limit: %d). Nothing to prune.",
                len(complete_sets),
                keep_limit,
            )
            return []

        retained_sets = complete_sets[:keep_limit]
        pruned_sets = complete_sets[keep_limit:]

        logger.info(
            "Retention policy: Keeping %d newest set(s) (%s to %s), pruning %d older set(s).",
            len(retained_sets),
            retained_sets[-1].timestamp,
            retained_sets[0].timestamp,
            len(pruned_sets),
        )

        for bset in pruned_sets:
            freed_bytes = bset.total_size_bytes
            files_to_remove = bset.all_files

            if dry_run:
                logger.info(
                    "[DRY-RUN] Would prune set %s (%d files, %.2f KiB)",
                    bset.timestamp,
                    len(files_to_remove),
                    freed_bytes / 1024.0,
                )
                continue

            for filepath in files_to_remove:
                try:
                    filepath.unlink(missing_ok=True)
                    logger.debug("Deleted file: %s", filepath.name)
                except OSError as exc:
                    logger.error("Failed to delete %s: %s", filepath, exc)

            logger.info(
                "Pruned backup set %s (%d files removed, %.2f KiB freed)",
                bset.timestamp,
                len(files_to_remove),
                freed_bytes / 1024.0,
            )

        return pruned_sets