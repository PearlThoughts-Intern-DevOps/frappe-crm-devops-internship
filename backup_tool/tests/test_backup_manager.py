"""Unit tests for Frappe CRM Backup & Restore Automation Tool."""

import datetime
import hashlib
import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from backup_tool.backup_manager import (
	EXIT_GENERAL_FAILURE,
	EXIT_INVALID_ARGS,
	EXIT_SUCCESS,
	EXIT_UNSAFE_RESTORE,
	EXIT_VERIFICATION_FAILURE,
	BackupManager,
	calculate_sha256,
	safe_resolve_child,
	sanitize_cmd,
	validate_safe_filename,
)


class TestBackupManager(unittest.TestCase):
	"""Test suite verifying backup, verification, retention, restore, and security logic."""

	def setUp(self):
		self.temp_dir = tempfile.TemporaryDirectory()
		self.backup_dir = Path(self.temp_dir.name)
		self.config = {
			"backup_dir": str(self.backup_dir),
			"source_site": "crm.localhost",
			"source_container": "crm-frappe-1",
			"retention_count": 7,
		}
		self.manager = BackupManager(self.config)

	def tearDown(self):
		self.temp_dir.cleanup()

	def test_sanitize_cmd_masks_sensitive_tokens(self):
		"""Ensure passwords and secrets are masked from logs."""
		cmd = ["bench", "restore", "dump.sql", "--mariadb-root-password", "supersecret123", "--force"]
		sanitized = sanitize_cmd(cmd)
		self.assertNotIn("supersecret123", sanitized)
		self.assertIn("******", sanitized)

		cmd2 = ["docker", "run", "-e", "MYSQL_ROOT_PASSWORD=topsecret", "mariadb:10.8"]
		sanitized2 = sanitize_cmd(cmd2)
		self.assertNotIn("topsecret", sanitized2)
		self.assertIn("MYSQL_ROOT_PASSWORD=******", sanitized2)

	def test_calculate_sha256(self):
		"""Verify accurate SHA-256 generation."""
		test_file = self.backup_dir / "sample.txt"
		test_content = b"DevOps internship task 2 verification test."
		test_file.write_bytes(test_content)

		expected_hash = hashlib.sha256(test_content).hexdigest()
		actual_hash = calculate_sha256(test_file)
		self.assertEqual(actual_hash, expected_hash)

	def _create_mock_backup(
		self,
		backup_id: str,
		content: bytes = b"test sql dump",
		ts: str | None = None,
		artifact_filename: str | None = None,
	) -> Path:
		"""Helper to create a mock backup directory with manifest and files."""
		dir_path = self.backup_dir / backup_id
		dir_path.mkdir(parents=True, exist_ok=True)

		fname = artifact_filename or f"{backup_id}-database.sql.gz"
		if "/" not in fname and "\\" not in fname and ".." not in fname:
			db_file = dir_path / fname
			db_file.write_bytes(content)
			db_hash = calculate_sha256(db_file)
		else:
			db_hash = hashlib.sha256(content).hexdigest()

		files_tar = dir_path / f"{backup_id}-files.tar.gz"
		files_tar.write_bytes(b"mock public files tar content")

		cfg_file = dir_path / f"{backup_id}-site_config_backup.json"
		cfg_file.write_bytes(b'{"encryption_key": "mockkey"}')

		manifest_data = {
			"backup_id": backup_id,
			"created_at": ts or datetime.datetime.now(datetime.timezone.utc).isoformat(),
			"source_site": "crm.localhost",
			"status": "complete",
			"artifacts": {
				"database": {
					"filename": fname,
					"size_bytes": len(content),
					"sha256": db_hash,
				},
				"public_files": {
					"filename": files_tar.name,
					"size_bytes": len(b"mock public files tar content"),
					"sha256": calculate_sha256(files_tar),
				},
				"site_config": {
					"filename": cfg_file.name,
					"size_bytes": len(b'{"encryption_key": "mockkey"}'),
					"sha256": calculate_sha256(cfg_file),
				},
			},
		}
		(dir_path / "manifest.json").write_text(json.dumps(manifest_data, indent=2))
		return dir_path

	def test_successful_checksum_verification(self):
		"""Verify that an intact backup passes verification with exit code 0."""
		self._create_mock_backup("backup_valid_01")
		code, report = self.manager.verify_backup("backup_valid_01")
		self.assertEqual(code, EXIT_SUCCESS)
		self.assertEqual(report["overall_status"], "PASS")

	def test_modified_file_checksum_failure(self):
		"""Verify that altering an artifact triggers SHA-256 failure with exit code 3."""
		backup_path = self._create_mock_backup("backup_tampered_01")
		db_file = backup_path / "backup_tampered_01-database.sql.gz"
		db_file.write_bytes(b"tampered content that does not match original digest")

		code, report = self.manager.verify_backup("backup_tampered_01")
		self.assertEqual(code, EXIT_VERIFICATION_FAILURE)
		self.assertEqual(report["overall_status"], "FAIL")

	def test_missing_artifact_detection(self):
		"""Verify that deleting an artifact triggers failure with exit code 3."""
		backup_path = self._create_mock_backup("backup_missing_file_01")
		db_file = backup_path / "backup_missing_file_01-database.sql.gz"
		db_file.unlink()

		code, report = self.manager.verify_backup("backup_missing_file_01")
		self.assertEqual(code, EXIT_VERIFICATION_FAILURE)
		self.assertEqual(report["overall_status"], "FAIL")

	def test_invalid_backup_id_handling(self):
		"""Verify non-existent backup ID returns invalid arguments code 2."""
		code, _ = self.manager.verify_backup("non_existent_backup_id_999")
		self.assertEqual(code, EXIT_INVALID_ARGS)

	def test_retention_keeps_exactly_latest_seven(self):
		"""Verify retention preserves the latest 7 verified backups and prunes older ones."""
		base_time = datetime.datetime(2026, 11, 1, 12, 0, 0, tzinfo=datetime.timezone.utc)
		for i in range(10):
			ts = (base_time + datetime.timedelta(hours=i)).isoformat()
			self._create_mock_backup(f"backup_seq_{i:02d}", ts=ts)

		code, report = self.manager.enforce_retention(keep_count=7)
		self.assertEqual(code, EXIT_SUCCESS)
		self.assertEqual(report["retained_count"], 7)
		self.assertEqual(report["deleted_count"], 3)
		self.assertIn("backup_seq_00", report["deleted_ids"])
		self.assertIn("backup_seq_01", report["deleted_ids"])
		self.assertIn("backup_seq_02", report["deleted_ids"])
		self.assertIn("backup_seq_09", report["retained_ids"])
		self.assertIn("backup_seq_03", report["retained_ids"])

	def test_incomplete_backups_not_treated_as_valid(self):
		"""Verify incomplete backups without manifest are not counted in retention."""
		self._create_mock_backup("backup_complete_01")
		incomplete_dir = self.backup_dir / "backup_incomplete_01"
		incomplete_dir.mkdir()
		(incomplete_dir / "some_partial.sql").write_text("incomplete dump")

		code, report = self.manager.enforce_retention(keep_count=7)
		self.assertEqual(code, EXIT_SUCCESS)
		self.assertEqual(report["total_verified"], 1)
		self.assertEqual(report["unverified_or_incomplete_count"], 1)
		self.assertTrue(incomplete_dir.exists())

	def test_restore_refuses_original_site(self):
		"""STRICT SAFETY CHECK: Restore must refuse crm.localhost with exit code 4."""
		code, report = self.manager.restore_backup(
			backup_id_or_path="backup_any",
			target_site="crm.localhost",
			target_container="crm-restore-test-frappe-1",
			target_compose_file="docker/docker-compose.restore-test.yml",
		)
		self.assertEqual(code, EXIT_UNSAFE_RESTORE)
		self.assertIn("blocked by security policy", report["error"])

	def test_restore_refuses_source_container(self):
		"""STRICT SAFETY CHECK: Restore must refuse targeting source application container."""
		code, report = self.manager.restore_backup(
			backup_id_or_path="backup_any",
			target_site="restore-test.localhost",
			target_container="crm-frappe-1",
			target_compose_file="docker/docker-compose.restore-test.yml",
		)
		self.assertEqual(code, EXIT_UNSAFE_RESTORE)
		self.assertIn("cannot be the primary application container", report["error"])

	@patch("backup_tool.backup_manager.run_command")
	def test_subprocess_failure_handling(self, mock_run_cmd):
		"""Verify subprocess failure in backup returns exit code 1 with logged error."""
		mock_run_cmd.side_effect = [
			(0, "true", ""),
			(0, "", ""),
			(1, "", "Bench backup crashed with out-of-disk-space error"),
		]
		code, report = self.manager.create_backup()
		self.assertEqual(code, EXIT_GENERAL_FAILURE)
		self.assertIn("Bench backup failed", report["error"])

	def test_security_path_traversal_in_backup_id_rejected(self):
		"""SECURITY: Verify that traversal sequences in backup_id are rejected."""
		code, report = self.manager.verify_backup("../../etc")
		self.assertEqual(code, EXIT_INVALID_ARGS)
		self.assertIn("error", report)

	def test_security_malicious_manifest_filename_traversal_rejected(self):
		"""SECURITY: Verify that traversal in manifest artifact filename is caught."""
		self._create_mock_backup("backup_evil_01", artifact_filename="../../etc/passwd")
		code, report = self.manager.verify_backup("backup_evil_01")
		self.assertEqual(code, EXIT_VERIFICATION_FAILURE)
		self.assertEqual(report["overall_status"], "FAIL")
		self.assertIn("../../etc/passwd", report["artifacts"])
		self.assertEqual(report["artifacts"]["../../etc/passwd"]["status"], "TRAVERSAL_DETECTED")

	def test_security_absolute_path_injection_in_manifest_rejected(self):
		"""SECURITY: Verify that absolute path injection in manifest is rejected."""
		abs_name = "C:\\Windows\\system32\\cmd.exe" if os.name == "nt" else "/etc/shadow"
		self._create_mock_backup("backup_evil_abs", artifact_filename=abs_name)
		code, report = self.manager.verify_backup("backup_evil_abs")
		self.assertEqual(code, EXIT_VERIFICATION_FAILURE)
		self.assertEqual(report["overall_status"], "FAIL")
		self.assertIn(abs_name, report["artifacts"])
		self.assertEqual(report["artifacts"][abs_name]["status"], "TRAVERSAL_DETECTED")

	def test_security_safe_resolve_child_rejects_escape(self):
		"""SECURITY: Verify safe_resolve_child rejects directory escape."""
		with self.assertRaises(ValueError):
			safe_resolve_child(self.backup_dir, "../outside_directory")

		with self.assertRaises(ValueError):
			safe_resolve_child(self.backup_dir, "dir/../../outside")

		# Valid nested child must succeed
		valid_child = safe_resolve_child(self.backup_dir, "valid_subdir")
		self.assertTrue(str(valid_child).startswith(str(self.backup_dir.resolve())))

	def test_security_validate_safe_filename(self):
		"""SECURITY: Verify validate_safe_filename rejects invalid and traversal characters."""
		self.assertEqual(validate_safe_filename("valid_backup.sql.gz"), "valid_backup.sql.gz")
		with self.assertRaises(ValueError):
			validate_safe_filename("../evil.sql")
		with self.assertRaises(ValueError):
			validate_safe_filename("sub/dir.sql")
		with self.assertRaises(ValueError):
			validate_safe_filename("dir\\file.sql")
		with self.assertRaises(ValueError):
			validate_safe_filename("")
		with self.assertRaises(ValueError):
			validate_safe_filename("evil\x00.sql")


if __name__ == "__main__":
	unittest.main()
