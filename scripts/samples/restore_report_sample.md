# Frappe CRM Test Environment Restoration Report

**Source Production Site:** `crm.localhost`  
**Target Test Environment:** `test.localhost`  
**Backup Timestamp Used:** `20261104_122524`  
**Restoration Duration:** `28.41s`  
**Status:** **SUCCESS**

---

## 1. Pre-Restoration Integrity Verification
Before modifying the target test database, the backup manager verified the integrity of source backup set `20261104_122524`:

| Artifact | File Name | Size | SHA-256 Checksum | Integrity Status |
| :--- | :--- | :--- | :--- | :---: |
| Database Dump | `20261104_122524-crm_localhost-database.sql.gz` | 315.1 KiB | `41aac26988503f9a6040622dac9e87bc8f31d27f4368374d9207205cb4585129` | ✅ VERIFIED |
| Public Files | `20261104_122524-crm_localhost-files.tar` | 10.0 KiB | `9b0e43085f5cf322426eaa4d4ac44543a81cebbf5bf1457d046e077d7218aed8` | ✅ VERIFIED |
| Private Files | `20261104_122524-crm_localhost-private-files.tar` | 10.0 KiB | `a778ae2921eef69f828631934cddef16c10e8ff2c439e1bcba3791997bec9832` | ✅ VERIFIED |
| Site Config | `20261104_122524-crm_localhost-site_config_backup.json` | 164.0 B | `5d35aba5526cda465e6eb4ae84ad4bbaf889d9293198a38735b8ed7e0354b21d` | ✅ VERIFIED |

---

## 2. MariaDB Compatibility & Stream Sanitization
- **Issue Detected:** MariaDB 11 client dump contained `/*M!100616 SET @OLD_NOTE_VERBOSITY` directives, which trigger `ERROR 1193` on MariaDB 10.8 server.
- **Remediation:** Automation tool dynamically sanitized SQL stream in a temporary decompression buffer.
- **Original Archive State:** Untouched and pristine (preserving valid SHA-256 signatures).

---

## 3. Post-Restoration Verification
- Restored site cache cleared via `bench --site test.localhost clear-cache`.
- CRM tables verified in target test database: **44 CRM DocType tables verified**.
- Leads, Deals, Organizations, and Form Scripts verified accessible.

