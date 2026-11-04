"""Unit tests. Run with:  python3 -m unittest discover -s tests -v

They use a mock `bench` script (tests/mock_bench/bench) in --local mode, so no
Docker or real Frappe is needed. They test the tool's logic, not Frappe itself.
"""
import json
import os
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
import frappe_backup as fb  # noqa: E402

MOCK_DIR = ROOT / "tests" / "mock_bench"


class ToolTests(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.bench = self.tmp / "bench"
        self.bench.mkdir()
        self.backups = self.tmp / "backups"
        self.reports = self.tmp / "reports"
        os.chmod(MOCK_DIR / "bench", 0o755)
        self._old_path = os.environ["PATH"]
        os.environ["PATH"] = f"{MOCK_DIR}:{self._old_path}"

    def tearDown(self):
        os.environ["PATH"] = self._old_path
        os.environ.pop("MOCK_TS", None)
        shutil.rmtree(self.tmp, ignore_errors=True)

    def cli(self, *extra, ts=None):
        if ts:
            os.environ["MOCK_TS"] = ts
        base = ["--local", "--bench-path", str(self.bench), "--site", "crm.localhost",
                "--backup-dir", str(self.backups), "--reports-dir", str(self.reports),
                "--log-file", str(self.tmp / "t.log")]
        return fb.main(base + list(extra))

    def test_backup_creates_manifest_and_reports(self):
        self.assertEqual(self.cli("backup", ts="20261104_100000"), 0)
        d = self.backups / "20261104_100000"
        manifest = json.loads((d / "manifest.json").read_text())
        self.assertEqual(len(manifest["files"]), 4)
        for f in manifest["files"]:
            self.assertEqual(fb.sha256_file(d / f["name"]), f["sha256"])
        self.assertTrue(list(self.reports.glob("backup_*.md")))
        self.assertTrue(list(self.reports.glob("verify_*.md")))

    def test_verify_detects_corruption(self):
        self.cli("backup", ts="20261104_100000")
        db = next((self.backups / "20261104_100000").glob("*database.sql.gz"))
        with open(db, "ab") as fh:
            fh.write(b"tampered")
        self.assertEqual(self.cli("verify", "20261104_100000"), fb.EXIT_VERIFY_FAILED)

    def test_verify_detects_missing_file(self):
        self.cli("backup", ts="20261104_100000")
        next((self.backups / "20261104_100000").glob("*private-files.tar")).unlink()
        self.assertEqual(self.cli("verify"), fb.EXIT_VERIFY_FAILED)

    def test_retention_keeps_latest_7(self):
        for i in range(10):
            self.assertEqual(self.cli("backup", ts=f"20261104_10000{i}"), 0)
        names = [d.name for d in fb.list_backups(self.backups, "crm.localhost")]
        self.assertEqual(len(names), 7)
        self.assertEqual(names[0], "20261104_100003")
        self.assertEqual(names[-1], "20261104_100009")

    def test_prune_dry_run_deletes_nothing(self):
        for i in range(9):
            self.cli("backup", "--no-prune", ts=f"20261104_10000{i}")
        self.cli("prune", "--dry-run")
        self.assertEqual(len(fb.list_backups(self.backups, "crm.localhost")), 9)

    def test_restore_refuses_same_container(self):
        self.cli("backup", ts="20261104_100000")
        os.environ[fb.PASSWORD_ENV] = "x"
        args = ["--container", "crm-frappe-1", "--backup-dir", str(self.backups),
                "--reports-dir", str(self.reports), "--log-file", str(self.tmp / "t.log"),
                "restore", "--test-container", "crm-frappe-1"]
        self.assertEqual(fb.main(args), fb.EXIT_ERROR)

    def test_restore_requires_password_env(self):
        os.environ.pop(fb.PASSWORD_ENV, None)
        args = ["--container", "crm-frappe-1", "--backup-dir", str(self.backups),
                "--reports-dir", str(self.reports), "--log-file", str(self.tmp / "t.log"),
                "restore", "--test-container", "crm-restore-test-frappe-1"]
        self.assertEqual(fb.main(args), fb.EXIT_ERROR)

    def test_failed_bench_leaves_no_partial_backup(self):
        (self.tmp / "badbin").mkdir()
        bad = self.tmp / "badbin" / "bench"
        bad.write_text("#!/usr/bin/env bash\necho boom >&2\nexit 1\n")
        bad.chmod(0o755)
        os.environ["PATH"] = f"{self.tmp / 'badbin'}:{self._old_path}"
        self.assertEqual(self.cli("backup"), fb.EXIT_ERROR)
        self.assertEqual(fb.list_backups(self.backups, "crm.localhost"), [])


if __name__ == "__main__":
    unittest.main()
