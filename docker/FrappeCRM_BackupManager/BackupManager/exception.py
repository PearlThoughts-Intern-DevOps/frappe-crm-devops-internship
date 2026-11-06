"""Custom exceptions for Frappe Backup Manager with distinct exit codes."""


class BackupManagerError(Exception):
    """Base exception for all backup manager errors."""
    exit_code: int = 1


class LockError(BackupManagerError):
    """Raised when another backup/restore process holds the execution lock."""
    exit_code: int = 2


class BenchCommandError(BackupManagerError):
    """Raised when an underlying Frappe Bench subprocess fails."""
    exit_code: int = 3


class VerificationError(BackupManagerError):
    """Raised when SHA-256 checksums or archive headers fail validation."""
    exit_code: int = 4


class RestoreError(BackupManagerError):
    """Raised when test-site restoration or post-restore smoke tests fail."""
    exit_code: int = 5