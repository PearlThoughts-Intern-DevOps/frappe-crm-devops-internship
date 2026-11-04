# Backup Verification Report

**Status: FAIL**

- **Backup ID:** 20261104_131616
- **Site:** crm.localhost
- **Verified at (UTC):** 2026-11-04T07:53:08+00:00

| File | SHA-256 | Expected | Actual | Integrity |
|---|---|---|---|---|
| 20261104_131616-crm_localhost-database.sql.gz | MISMATCH | 485fd8662103ac10… | 6de255a005f1a12f… | FAILED — BadGzipFile: Not a gzipped file (b'ta') |
| 20261104_131616-crm_localhost-files.tar | OK | f17ac657aba3b2c3… | f17ac657aba3b2c3… | OK — tar OK (1 entries) |
| 20261104_131616-crm_localhost-private-files.tar | OK | 9ae11c83e9df8b49… | 9ae11c83e9df8b49… | OK — tar OK (1 entries) |
| 20261104_131616-crm_localhost-site_config_backup.json | OK | 9598dab6c4c17f26… | 9598dab6c4c17f26… | OK — JSON OK |
