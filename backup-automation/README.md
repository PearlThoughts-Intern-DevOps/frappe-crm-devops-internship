# Frappe CRM Backup and Restore Automation

## 1. Project Overview

This project implements a Python-based backup and restore automation tool for Frappe CRM using Frappe Bench commands.

The tool automates database and file backups, generates SHA-256 checksums to verify backup integrity, manages backup retention, and supports restoration into a separate test environment.

The project aims to make the backup and recovery process more reliable, repeatable, and easier to manage.

## 2. Features

- **Automated Backups:** Creates database and file backups using Frappe Bench.
- **SHA-256 Verification:** Generates checksums and verifies backup file integrity.
- **Backup Retention:** Keeps the latest 7 backups and removes older backups.
- **Restore Support:** Provides an option to restore backups into a separate test site.
- **Logging:** Records backup and restore operations.
- **Error Handling:** Handles command failures and reports errors.
- **Command-Line Interface:** Supports backup, verification, listing, cleanup, and restore operations.

## 3. Project Structure

```text
backup-automation/
│
├── backup_restore.py
├── README.md
├── .gitignore
│
└── reports/
    ├── backup_report_20261104_174026.txt
    └── verification_report_20261104_174026.txt
```

## 4. Requirements

- Python 3
- Frappe Bench
- A running Frappe CRM environment
- Docker (if running Frappe inside Docker)
- Access to the Frappe site and its database

The Python script uses standard Python libraries, so no additional Python packages are required.

## 5. Configuration

The script uses the following default configuration:

| Setting | Default |
|---|---|
| Bench directory | `/home/frappe/frappe-bench` |
| Frappe site | `crm.localhost` |
| Backup location | Frappe site's private backups directory |
| Log location | `/home/frappe/logs/backup_tool.log` |
| Reports location | `/home/frappe/reports/` |
| Backup retention | 7 backups |

The bench directory and site can be overridden using the script's command-line options.

## 6. Usage

Run the following commands from the Frappe container.

### Create a Backup

```bash
python3 /home/frappe/backup_restore.py backup
```

This command:
- Runs the Frappe Bench backup command.
- Creates database, public files, private files, and site configuration backups.
- Generates SHA-256 checksums.
- Verifies the generated backup files.
- Saves a backup report.
- Applies the retention policy.

### List Available Backups

```bash
python3 /home/frappe/backup_restore.py list
```

Displays the available backup identifiers.

### Verify a Backup

```bash
python3 /home/frappe/backup_restore.py verify --id latest
```

Verifies the backup files using their stored SHA-256 checksums and generates a verification report.

### Apply Backup Retention

```bash
python3 /home/frappe/backup_restore.py cleanup --keep 7
```

Keeps the latest seven backups and removes older backup sets.

### Restore a Backup

```bash
python3 /home/frappe/backup_restore.py restore --test-site test.localhost
```

Restores a selected backup into a separate test site rather than overwriting the original CRM site.

**Important:** Ensure the target test site exists before restoration. Verify the database compatibility of the backup before restoring it.

## 7. Docker Usage

When Frappe is running in Docker, the commands can be executed using `docker exec`.

Example:

```powershell
docker exec -it crm-frappe-1 python3 /home/frappe/backup_restore.py backup
```

List backups:

```powershell
docker exec -it crm-frappe-1 python3 /home/frappe/backup_restore.py list
```

Verify the latest backup:

```powershell
docker exec -it crm-frappe-1 python3 /home/frappe/backup_restore.py verify --id latest
```

Run cleanup:

```powershell
docker exec -it crm-frappe-1 python3 /home/frappe/backup_restore.py cleanup --keep 7
```

Restore into a test site:

```powershell
docker exec -it -w /home/frappe/frappe-bench crm-frappe-1 python3 /home/frappe/backup_restore.py restore --test-site test.localhost
```

## 8. Backup Verification

SHA-256 checksums are generated for the backup files.

During testing, the following files passed verification:

- Database backup
- Public files backup
- Private files backup
- Site configuration backup

The verification report records the checksum verification results.

A sample report is included in the `reports/` directory.

## 9. Backup and Restore Testing

The following operations were performed during project testing:

| Test | Result |
|---|---|
| Frappe Bench backup | Successful |
| Database backup | Successful |
| Public files backup | Successful |
| Private files backup | Successful |
| SHA-256 verification | Passed for all four files |
| Backup listing | Successful |
| Retention cleanup command | Executed |
| Test site creation | Successful |
| Test site restoration | Successful |

The original site was `crm.localhost`, and the separate restore destination was `test.localhost`.

### Database Compatibility Note

During restoration testing, the MariaDB 10.8.8 server rejected the `NOTE_VERBOSITY` session-setting statements present in the SQL backup.

A temporary compatible copy of the SQL dump was created by removing the unsupported session-setting statements. The original backup was preserved, and restoration into `test.localhost` then completed successfully.

This compatibility workaround was performed during testing; database compatibility should be checked when restoring backups across different MariaDB versions.

## 10. Security Considerations

- Do not commit database backup files to GitHub.
- Do not expose database passwords or credentials.
- Do not commit sensitive site configuration files.
- Keep backup files in a secure location.
- Restore backups into a separate test environment whenever possible.
- Protect backup reports and logs if they contain sensitive information.

## 11. Sample Reports

The `reports/` directory contains sample output from the backup and verification operations:

- `backup_report_20261104_174026.txt`
- `verification_report_20261104_174026.txt`

These reports provide evidence of the backup operation and SHA-256 verification results.

## 12. Conclusion

This project demonstrates Python automation for Frappe CRM backup and recovery operations using Frappe Bench.

It includes automated backup creation, SHA-256 integrity verification, backup retention, logging, error handling, and test-environment restoration support.

The implementation helps simplify backup management and provides a repeatable approach to testing recovery procedures.