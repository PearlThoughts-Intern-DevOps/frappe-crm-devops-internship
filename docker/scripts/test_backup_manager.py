#!/usr/bin/env python3
"""
Unit Tests for Frappe CRM Backup & Restore Automation Tool
==========================================================
Tests SHA-256 calculation, archive integrity checks, retention logic,
manifest generation, and SQL sanitization.
"""

import gzip
import io
import json
import os
import shutil
import tarfile
import tempfile
import unittest
from pathlib import Path

# Import the module to test
from frappe_backup_manager import (
    BackupSet,
    IntegrityVerifier,
    RetentionManager,
    FrappeBackupManager,
    format_size,
)


class TestFormatSize(unittest.TestCase):
    def test_format_size_bytes(self):
        self.assertEqual(format_size(500), "500.0 B")

    def test_format_size_kib(self):
        self.assertEqual(format_size(2048), "2.0 KiB")

    def test_format_size_mib(self):
        self.assertEqual(format_size(5 * 1024 * 1024), "5.0 MiB")


class TestIntegrityVerifier(unittest.TestCase):
    def setUp(self):
        self.test_dir = Path(tempfile.mkdtemp())
        self.verifier = IntegrityVerifier()

    def tearDown(self):
        shutil.rmtree(self.test_dir)

    def test_sha256_calculation(self):
        sample_file = self.test_dir / "sample.txt"
        sample_file.write_text("Hello Frappe CRM Automation!", encoding="utf-8")
        
        # Expected SHA-256 of "Hello Frappe CRM Automation!"
        import hashlib
        expected = hashlib.sha256(b"Hello Frappe CRM Automation!").hexdigest()
        calculated = self.verifier.calculate_sha256(sample_file)
        self.assertEqual(calculated, expected)

    def test_valid_gzip_integrity(self):
        gz_file = self.test_dir / "valid.sql.gz"
        with gzip.open(gz_file, "wt", encoding="utf-8") as f:
            f.write("CREATE TABLE test (id int);")
        
        ok, err = self.verifier.test_archive_integrity(gz_file)
        self.assertTrue(ok)
        self.assertIsNone(err)

    def test_corrupt_gzip_integrity(self):
        gz_file = self.test_dir / "corrupt.sql.gz"
        # Write corrupted gzip header / contents
        gz_file.write_bytes(b"\x1f\x8b\x08\x00corrupted_data_not_valid_gzip")
        
        ok, err = self.verifier.test_archive_integrity(gz_file)
        self.assertFalse(ok)
        self.assertIsNotNone(err)

    def test_valid_tar_integrity(self):
        tar_file = self.test_dir / "valid.tar"
        dummy_file = self.test_dir / "dummy.txt"
        dummy_file.write_text("some test content")
        with tarfile.open(tar_file, "w") as tar:
            tar.add(dummy_file, arcname="dummy.txt")
        
        ok, err = self.verifier.test_archive_integrity(tar_file)
        self.assertTrue(ok)
        self.assertIsNone(err)

    def test_corrupt_tar_integrity(self):
        tar_file = self.test_dir / "corrupt.tar"
        tar_file.write_bytes(b"not a tar archive random string")
        
        ok, err = self.verifier.test_archive_integrity(tar_file)
        self.assertFalse(ok)
        self.assertIn("Not a valid TAR", err)

    def test_valid_json_integrity(self):
        json_file = self.test_dir / "valid.json"
        json_file.write_text('{"status": "ok", "retention": 7}')
        
        ok, err = self.verifier.test_archive_integrity(json_file)
        self.assertTrue(ok)
        self.assertIsNone(err)

    def test_corrupt_json_integrity(self):
        json_file = self.test_dir / "corrupt.json"
        json_file.write_text('{"status": "truncated')
        
        ok, err = self.verifier.test_archive_integrity(json_file)
        self.assertFalse(ok)


class TestRetentionManager(unittest.TestCase):
    def setUp(self):
        self.test_dir = Path(tempfile.mkdtemp())
        self.retention = RetentionManager()
        self.site = "crm.localhost"

        # Create 10 mock backup sets
        for i in range(1, 11):
            ts = f"202611{i:02d}_120000"
            (self.test_dir / f"{ts}-crm_localhost-database.sql.gz").write_bytes(b"db" * 100)
            (self.test_dir / f"{ts}-crm_localhost-files.tar").write_bytes(b"files" * 50)
            (self.test_dir / f"{ts}-crm_localhost-site_config_backup.json").write_bytes(b"{}")
            (self.test_dir / f"{ts}-crm_localhost-checksums.sha256").write_bytes(b"hash")

    def tearDown(self):
        shutil.rmtree(self.test_dir)

    def test_discover_backup_sets(self):
        sets = self.retention.discover_backup_sets(self.test_dir, self.site)
        self.assertEqual(len(sets), 10)
        # Verify sorted newest first
        self.assertEqual(sets[0].timestamp, "20261110_120000")
        self.assertEqual(sets[-1].timestamp, "20261101_120000")

    def test_retention_policy_keep_7(self):
        sets = self.retention.discover_backup_sets(self.test_dir, self.site)
        report = self.retention.enforce_retention(sets, keep_count=7, dry_run=False)
        
        self.assertEqual(report["total_found"], 10)
        self.assertEqual(report["retention_limit"], 7)
        self.assertEqual(report["retained_count"], 7)
        self.assertEqual(report["pruned_count"], 3)
        self.assertGreater(report["bytes_freed"], 0)

        # Confirm remaining files in directory
        remaining = self.retention.discover_backup_sets(self.test_dir, self.site)
        self.assertEqual(len(remaining), 7)
        # Ensure oldest 3 (Nov 1, 2, 3) were removed
        timestamps = [s.timestamp for s in remaining]
        self.assertNotIn("20261101_120000", timestamps)
        self.assertNotIn("20261102_120000", timestamps)
        self.assertNotIn("20261103_120000", timestamps)
        self.assertIn("20261110_120000", timestamps)

    def test_retention_dry_run(self):
        sets = self.retention.discover_backup_sets(self.test_dir, self.site)
        report = self.retention.enforce_retention(sets, keep_count=7, dry_run=True)
        
        self.assertTrue(report["dry_run"])
        self.assertEqual(report["pruned_count"], 3)
        # In dry run, files should NOT have been deleted
        remaining = self.retention.discover_backup_sets(self.test_dir, self.site)
        self.assertEqual(len(remaining), 10)


class TestSqlSanitizer(unittest.TestCase):
    def setUp(self):
        self.test_dir = Path(tempfile.mkdtemp())
        self.manager = FrappeBackupManager(bench_dir=self.test_dir)

    def tearDown(self):
        shutil.rmtree(self.test_dir)

    def test_sanitize_mariadb11_directive(self):
        sql_file = self.test_dir / "dump.sql.gz"
        content = (
            "/*!40101 SET NAMES utf8mb4 */;\n"
            "/*M!100616 SET @OLD_NOTE_VERBOSITY=@@NOTE_VERBOSITY, NOTE_VERBOSITY=0 */;\n"
            "CREATE TABLE test (id int);\n"
            "/*M!100616 SET NOTE_VERBOSITY=@OLD_NOTE_VERBOSITY */;\n"
        )
        with gzip.open(sql_file, "wt", encoding="utf-8") as gz:
            gz.write(content)

        sanitized_path = self.manager.sanitize_sql_dump_if_needed(sql_file)
        self.assertNotEqual(sanitized_path, sql_file)

        # Read sanitized file
        with gzip.open(sanitized_path, "rt", encoding="utf-8") as gz:
            sanitized_content = gz.read()

        self.assertNotIn("NOTE_VERBOSITY", sanitized_content)
        self.assertIn("CREATE TABLE test (id int);", sanitized_content)

        # Cleanup temp file
        if sanitized_path.exists():
            sanitized_path.unlink()


if __name__ == "__main__":
    unittest.main()
