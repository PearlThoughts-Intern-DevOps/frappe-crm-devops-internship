#!/usr/bin/env python3
"""Top-level CLI executable wrapper for the backup_manager package."""

from pathlib import Path
import sys

# Ensure the 'scripts/' directory is on sys.path so `import backup_manager` resolves
sys.path.insert(0, str(Path(__file__).resolve().parent))

from BackupManager.cli import main

if __name__ == "__main__":
    sys.exit(main())