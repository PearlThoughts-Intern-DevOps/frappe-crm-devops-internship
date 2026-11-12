"""Data models and filesystem discovery for Frappe Backup Sets."""

from dataclasses import dataclass
import logging
from pathlib import Path
import re
from typing import Optional

logger = logging.getLogger(__name__)

SUFFIX_MAP: dict[str, str] = {
    "database.sql.gz": "database",
    "files.tar": "public_files",
    "private-files.tar": "private_files",
    "site_config_backup.json": "site_config",
    "manifest.json": "manifest",
    "checksums.sha256": "checksum_file",
}


@dataclass
class BackupSet:
    """Represents an atomic point-in-time Frappe backup set sharing a timestamp prefix."""

    timestamp: str
    site: str
    database: Optional[Path] = None
    public_files: Optional[Path] = None
    private_files: Optional[Path] = None
    site_config: Optional[Path] = None
    manifest: Optional[Path] = None
    checksum_file: Optional[Path] = None

    @property
    def core_artifacts(self) -> dict[str, Optional[Path]]:
        """Returns the 4 mandatory Frappe backup artifacts."""
        return {
            "database": self.database,
            "public_files": self.public_files,
            "private_files": self.private_files,
            "site_config": self.site_config,
        }

    @property
    def is_complete(self) -> bool:
        """True if all 4 mandatory Frappe backup artifacts exist on disk."""
        return all(
            path is not None and path.is_file()
            for path in self.core_artifacts.values()
        )

    @property
    def is_verified(self) -> bool:
        """True if both the manifest and sha256 checksum files exist on disk."""
        return (
            self.manifest is not None
            and self.manifest.is_file()
            and self.checksum_file is not None
            and self.checksum_file.is_file()
        )

    @property
    def all_files(self) -> list[Path]:
        """Returns all existing file paths associated with this backup set."""
        candidates = [
            self.database,
            self.public_files,
            self.private_files,
            self.site_config,
            self.manifest,
            self.checksum_file,
        ]
        return [p for p in candidates if p is not None and p.exists()]

    @property
    def total_size_bytes(self) -> int:
        """Total size in bytes across all files in this backup set."""
        return sum(p.stat().st_size for p in self.all_files)


def discover_backup_sets(
    backup_dir: Path, site: str, site_slug: str
) -> list[BackupSet]:
    """
    Scans backup_dir and groups files into BackupSet instances sorted newest-first.
    Matches pattern: YYYYMMDD_HHMMSS-<site_slug>-<artifact_suffix>
    """
    if not backup_dir.exists():
        logger.warning("Backup directory does not exist yet: %s", backup_dir)
        return []

    pattern = re.compile(rf"^(\d{{8}}_\d{{6}})-{re.escape(site_slug)}-(.+)$")
    sets_by_ts: dict[str, BackupSet] = {}

    for entry in backup_dir.iterdir():
        if not entry.is_file():
            continue

        match = pattern.match(entry.name)
        if not match:
            continue

        timestamp, suffix = match.group(1), match.group(2)
        attr_name = SUFFIX_MAP.get(suffix)
        if not attr_name:
            continue

        if timestamp not in sets_by_ts:
            sets_by_ts[timestamp] = BackupSet(timestamp=timestamp, site=site)

        setattr(sets_by_ts[timestamp], attr_name, entry)

    sorted_sets = sorted(
        sets_by_ts.values(), key=lambda s: s.timestamp, reverse=True
    )
    logger.debug(
        "Discovered %d backup set(s) for site '%s' in %s",
        len(sorted_sets),
        site,
        backup_dir,
    )
    return sorted_sets