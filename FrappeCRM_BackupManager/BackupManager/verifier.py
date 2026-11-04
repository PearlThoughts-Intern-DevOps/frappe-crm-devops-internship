"""Archive structural inspection, streaming SHA-256 computation, and manifest verification."""

from datetime import datetime, timezone
import gzip
import hashlib
import json
import logging
from pathlib import Path
import tarfile
from typing import Any
import zlib

from .exception import VerificationError
from .models import BackupSet

logger = logging.getLogger(__name__)

CHUNK_SIZE = 65536  # 64 KB


class IntegrityVerifier:
    """Validates backup archive headers/trailers and verifies SHA-256 digests."""

    @staticmethod
    def compute_sha256(filepath: Path) -> str:
        """Streams a file in 64 KB chunks to compute its SHA-256 hex digest."""
        sha256 = hashlib.sha256()
        try:
            with open(filepath, "rb") as f:
                for chunk in iter(lambda: f.read(CHUNK_SIZE), b""):
                    sha256.update(chunk)
        except OSError as exc:
            raise VerificationError(f"Failed to read file for hashing {filepath}: {exc}") from exc
        return sha256.hexdigest()

    @staticmethod
    def _verify_gzip(filepath: Path) -> None:
        """Verifies gzip magic header and streams to EOF to validate CRC32 trailer."""
        if filepath.stat().st_size == 0:
            raise VerificationError(f"Database archive is 0 bytes: {filepath.name}")

        with open(filepath, "rb") as raw_f:
            magic = raw_f.read(2)
            if magic != b"\x1f\x8b":
                raise VerificationError(
                    f"Invalid gzip magic header in {filepath.name}: expected 1f8b, got {magic.hex()}"
                )

        uncompressed_bytes = 0
        try:
            with gzip.open(filepath, "rb") as gz_f:
                while chunk := gz_f.read(CHUNK_SIZE):
                    uncompressed_bytes += len(chunk)
        except (OSError, EOFError, zlib.error) as exc:
            raise VerificationError(
                f"Corrupt or truncated gzip archive {filepath.name}: {exc}"
            ) from exc

        if uncompressed_bytes == 0:
            raise VerificationError(
                f"Gzip archive {filepath.name} decompressed to 0 bytes (empty SQL dump)."
            )

    @staticmethod
    def _verify_tar(filepath: Path) -> None:
        """Verifies that a .tar archive has valid, non-truncated member headers."""
        if not tarfile.is_tarfile(filepath):
            raise VerificationError(f"File is not a valid TAR archive: {filepath.name}")
        try:
            with tarfile.open(filepath, "r") as tar:
                tar.getmembers()
        except (tarfile.TarError, EOFError, OSError) as exc:
            raise VerificationError(
                f"Corrupt or truncated TAR archive {filepath.name}: {exc}"
            ) from exc

    @staticmethod
    def _verify_site_config(filepath: Path) -> None:
        """Verifies that site_config_backup.json is valid JSON containing DB keys."""
        try:
            data = json.loads(filepath.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError) as exc:
            raise VerificationError(
                f"Invalid JSON in {filepath.name}: {exc}"
            ) from exc

        if not isinstance(data, dict) or "db_name" not in data:
            raise VerificationError(
                f"Missing required 'db_name' key in {filepath.name}"
            )

    def validate_structure(self, backup_set: BackupSet) -> None:
        """Performs deep format checks on all 4 core artifacts in a BackupSet."""
        if not backup_set.is_complete:
            missing = [k for k, v in backup_set.core_artifacts.items() if v is None or not v.exists()]
            raise VerificationError(
                f"Backup set {backup_set.timestamp} is incomplete. Missing: {', '.join(missing)}"
            )

        logger.debug("Validating archive structure for backup set %s...", backup_set.timestamp)
        assert backup_set.database is not None
        assert backup_set.public_files is not None
        assert backup_set.private_files is not None
        assert backup_set.site_config is not None

        self._verify_gzip(backup_set.database)
        self._verify_tar(backup_set.public_files)
        self._verify_tar(backup_set.private_files)
        self._verify_site_config(backup_set.site_config)
        logger.debug("Structural validation passed for backup set %s.", backup_set.timestamp)

    def generate_manifests(self, backup_set: BackupSet, site_slug: str) -> dict[str, Any]:
        """
        Validates structure, computes SHA-256 digests, and writes both
        <ts>-<site_slug>-manifest.json and <ts>-<site_slug>-checksums.sha256.
        """
        self.validate_structure(backup_set)

        assert backup_set.database is not None
        backup_dir = backup_set.database.parent
        prefix = f"{backup_set.timestamp}-{site_slug}"

        manifest_path = backup_dir / f"{prefix}-manifest.json"
        checksum_path = backup_dir / f"{prefix}-checksums.sha256"

        artifacts_meta: dict[str, dict[str, Any]] = {}
        sha256_lines: list[str] = []

        for key, filepath in backup_set.core_artifacts.items():
            assert filepath is not None
            digest = self.compute_sha256(filepath)
            size_bytes = filepath.stat().st_size

            artifacts_meta[key] = {
                "filename": filepath.name,
                "size_bytes": size_bytes,
                "sha256": digest,
            }
            # Standard GNU coreutils sha256sum format uses two spaces
            sha256_lines.append(f"{digest}  {filepath.name}")
            logger.info("Computed SHA-256 for %-13s: %s (%d bytes)", key, digest[:16] + "...", size_bytes)

        manifest_data: dict[str, Any] = {
            "backup_id": backup_set.timestamp,
            "site": backup_set.site,
            "timestamp_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "status": "VERIFIED",
            "artifacts": artifacts_meta,
        }

        manifest_path.write_text(json.dumps(manifest_data, indent=2) + "\n", encoding="utf-8")
        checksum_path.write_text("\n".join(sha256_lines) + "\n", encoding="utf-8")

        backup_set.manifest = manifest_path
        backup_set.checksum_file = checksum_path

        logger.info("Generated manifest: %s", manifest_path.name)
        return manifest_data

    def verify_backup_set(self, backup_set: BackupSet) -> dict[str, Any]:
        """
        Verifies an existing backup set against its stored manifest.json
        and performs deep structural checks on all archives.
        """
        self.validate_structure(backup_set)

        if backup_set.manifest is None or not backup_set.manifest.is_file():
            raise VerificationError(
                f"Manifest file missing for backup set {backup_set.timestamp}. Cannot verify checksums."
            )

        try:
            manifest_data = json.loads(backup_set.manifest.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError) as exc:
            raise VerificationError(
                f"Failed to parse manifest file {backup_set.manifest.name}: {exc}"
            ) from exc

        recorded_artifacts = manifest_data.get("artifacts", {})
        for key, filepath in backup_set.core_artifacts.items():
            assert filepath is not None
            if key not in recorded_artifacts:
                raise VerificationError(
                    f"Artifact '{key}' missing from manifest {backup_set.manifest.name}"
                )

            expected_hash = recorded_artifacts[key].get("sha256")
            expected_size = recorded_artifacts[key].get("size_bytes")

            actual_size = filepath.stat().st_size
            if actual_size != expected_size:
                raise VerificationError(
                    f"Size mismatch for {filepath.name}: expected {expected_size} B, got {actual_size} B"
                )

            actual_hash = self.compute_sha256(filepath)
            if actual_hash != expected_hash:
                raise VerificationError(
                    f"SHA-256 mismatch for {filepath.name}: expected {expected_hash}, got {actual_hash}"
                )

            logger.info("Verified %-13s: OK (%s)", key, actual_hash[:16] + "...")

        return manifest_data