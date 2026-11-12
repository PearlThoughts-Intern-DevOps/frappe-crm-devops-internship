#!/usr/bin/env python3
"""Frappe CRM Docker Container Monitoring & Auto-Recovery CLI Entrypoint."""

import sys
from pathlib import Path

# Ensure package directory is on sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent))

from DockerMonitor.cli import main

if __name__ == "__main__":
	sys.exit(main())
