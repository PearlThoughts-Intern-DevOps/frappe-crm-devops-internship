"""Configuration management and path resolution for Frappe Backup Manager."""

from dataclasses import dataclass, field
import os
from pathlib import Path
from typing import Optional


def _default_bench_path() -> Path:
    """Detects bench root from env, relative script location, or standard container path."""
    # 1. Check if explicitly set via environment variable
    env_path = os.getenv("FRAPPE_BENCH_PATH")
    if env_path:
        return Path(env_path).resolve()

    # 2. Check if this script lives inside <bench-root>/scripts/backup_manager/config.py
    candidate = Path(__file__).resolve().parents[2]
    if (candidate / "sites").is_dir():
        return candidate

    # 3. Fallback to standard Frappe Docker container path
    return Path("/home/frappe/frappe-bench")


@dataclass
class BackupConfig:
    """Centralized configuration state for backup, verification, retention, and restore."""

    site: str = "crm.localhost"
    test_site: str = "crm-test.localhost"
    bench_path: Path = field(default_factory=_default_bench_path)
    container_bench_path: Path = Path("/home/frappe/frappe-bench")
    container_name: Optional[str] = field(
        default_factory=lambda: os.getenv("FRAPPE_CONTAINER_NAME", "crm-frappe-1")
    )
    retention_count: int = 7
    db_root_password: str = field(
        default_factory=lambda: os.getenv("FRAPPE_DB_ROOT_PASSWORD", "123")
    )
    admin_password: str = field(
        default_factory=lambda: os.getenv("FRAPPE_ADMIN_PASSWORD", "admin")
    )
    log_file: Path = field(
        default_factory=lambda: Path(__file__).resolve().parents[2] / "logs" / "backups.log"
    )
    verbose: bool = False

    def __post_init__(self) -> None:
        """Normalize path types and validate basic constraints."""
        self.bench_path = Path(self.bench_path).resolve()
        self.container_bench_path = Path(self.container_bench_path)
        self.log_file = Path(self.log_file).resolve()

        if self.retention_count < 1:
            raise ValueError(f"retention_count must be >= 1, got {self.retention_count}")
        if self.site == self.test_site:
            raise ValueError(
                f"Safety violation: test_site ('{self.test_site}') cannot be identical to production site ('{self.site}')."
            )

    @property
    def site_slug(self) -> str:
        """Returns the Frappe-normalized site slug used in backup filenames."""
        return self.site.replace(".", "_").replace("-", "_")

    @property
    def sites_dir(self) -> Path:
        """Path to the bench 'sites/' directory."""
        return self.bench_path / "sites"

    @property
    def backup_dir(self) -> Path:
        """Path where Frappe writes backup artifacts for the primary site."""
        return self.sites_dir / self.site / "private" / "backups"

    @property
    def test_site_dir(self) -> Path:
        """Path to the target test site directory."""
        return self.sites_dir / self.test_site

    @property
    def test_site_config_path(self) -> Path:
        """Path to the target test site's site_config.json."""
        return self.test_site_dir / "site_config.json"