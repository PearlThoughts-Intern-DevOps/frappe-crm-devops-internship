# Task 2: Python Backup and Restore Automation for Frappe CRM

## 1. Project Overview

This project implements a Python-based automation tool to perform backup, verification, retention, and restoration operations for a Frappe CRM application.

The tool uses Frappe Bench commands to create backups, Python's `hashlib` library to generate SHA-256 checksums, and Docker commands to interact with the running Frappe container.

The objective is to simplify backup and restore operations while maintaining backup integrity and providing a reliable recovery process.

## 2. Project Objectives

- Automate Frappe CRM backups using Python.
- Back up the database and public/private files.
- Generate SHA-256 checksums to verify backup integrity.
- Implement a retention policy to keep the latest seven backups inside the container.
- Restore backups to a separate test site.
- Maintain logs of backup, verification, and restore operations.
- Provide a command-line interface (CLI) for executing operations.

## 3. Technologies and Tools Used

| Technology | Purpose |
|---|---|
| Python | Main programming language used to automate backup and restore operations. |
| Docker | Runs the Frappe CRM application and its supporting services in containers. |
| Frappe Bench | Command-line tool used to manage Frappe sites, applications, backups, and restores. |
| Frappe CRM | The application being backed up and restored. |
| MariaDB | Relational database used by Frappe CRM to store application data. |
| Linux Shell | Executes commands inside the Frappe Docker container. |
| PowerShell | Used on Windows to run the Python script and manage project files. |
| SHA-256 | Cryptographic hashing algorithm used to verify backup file integrity. |
| JSON | Stores backup checksum information in a structured format. |
| Git and GitHub | Used for source-code version control and project submission. |

## 4. Important Terms Explained

- **Backup:** A copy of application data that can be used to recover information if the original data is lost or damaged.
- **Restore:** The process of recovering application data from a previously created backup.
- **Database:** An organized collection of information. Frappe CRM uses MariaDB to store records such as users, customers, and application settings.
- **Frappe Bench:** A command-line utility that manages Frappe applications and sites. It supports operations such as creating backups, restoring sites, and managing applications.
- **Docker Container:** An isolated environment in which an application or service runs with its required dependencies.
- **SHA-256:** A hashing algorithm that generates a fixed-length 256-bit fingerprint for a file.
- **Checksum:** A value generated from file contents. Comparing checksums helps identify whether a backup file has changed or become corrupted.
- **Manifest:** A structured file that records backup filenames and their corresponding checksum values.
- **Retention Policy:** A rule that determines how long backups are kept. This project keeps the latest seven database backup sets inside the container.
- **CLI (Command-Line Interface):** A way to interact with a program by entering commands in a terminal.
- **Logging:** Recording important application activities, errors, and operation results in a log file.
- **Public Files:** Files uploaded to a Frappe site that are publicly accessible through the application.
- **Private Files:** Files uploaded to a Frappe site that require permission or authentication to access.
- **Rollback/Recovery:** Returning an application to a previously working state using a backup.

## 5. Project Architecture

```text
                  Windows System
                       |
                       |
                Python Automation
                    backup.py
                       |
          +------------+-------------+
          |            |             |
          v            v             v
       Backup       Verify       Retention
          |            |             |
          v            v             v
     Docker Exec   SHA-256       Keep Latest 7
          |        Checksums      Backups
          |
          v
    Frappe Container
          |
          v
      Frappe Bench
          |
          v
    crm-task1.localhost
          |
          v
   Database + Site Files
          |
          v
     Backup Directory
          |
          v
    Restore to Separate
       Test Site
```

## 6. Project Structure

```text
task2-backup-restore/
│
├── backup.py
├── README.md
├── backup.log
├── checksum_manifest.json
│
└── backups/
    └── 20261107_203706/
        ├── database.sql.gz
        ├── site_config_backup.json
        ├── files.tar
        ├── private-files.tar
        └── checksum_manifest.json
```

*Note: Actual backup filenames include a timestamp and site name. The structure above is simplified for documentation.*

**Security note:** Backup files and site configuration files may contain sensitive information. Do not commit real database backups, private files, credentials, or unsanitized configuration files to a public GitHub repository.

## 7. Backup Process

The Python script executes the Frappe Bench backup command inside the running Frappe container.

Command used:

```bash
bench --site crm-task1.localhost backup --with-files
```

This creates backup files for:

1. Database
2. Site configuration
3. Public files
4. Private files

The generated backup files are copied from the Docker container to the local Windows backup directory.

A timestamp-based folder is created for each backup.

## 8. Checksum Verification

The project uses Python's `hashlib` library to generate SHA-256 checksums.

Each backup file is processed to generate a unique hash value. These values are stored in `checksum_manifest.json`.

During verification:

1. The script reads the checksum manifest.
2. It checks whether the backup files exist.
3. It calculates the SHA-256 checksum again.
4. It compares the calculated checksum with the stored checksum.
5. It reports whether verification succeeded or failed.

Example:

```text
Backup file: database.sql.gz
Expected checksum: Stored in manifest
Actual checksum: Recalculated by Python
Result: Match / Mismatch
```

If a file is missing or its checksum does not match, verification fails.

## 9. Retention Policy

The retention policy prevents unlimited accumulation of backup files inside the Frappe container.

The script:

- Identifies database backup files.
- Sorts them by timestamp, newest first.
- Keeps the latest seven backup sets.
- Deletes older backup files belonging to those backup sets.

**Important:** The implemented retention policy applies to backups inside the Docker container. It does not automatically delete local Windows backup folders.

## 10. Restore Process

The restore operation recovers a selected backup into a separate Frappe test site.

Example command:

```bash
python backup.py restore --timestamp 20261107_203706 --target-site crm-restore-cli.localhost
```

The process follows these steps:

1. Selects the backup using its timestamp.
2. Verifies the backup using SHA-256 checksums.
3. Checks that the required database and file backups exist.
4. Requests confirmation from the user by asking them to type `RESTORE`.
5. Copies backup files into a temporary directory inside the Frappe container.
6. Restores the database and public/private files using Frappe Bench.
7. Records the result in the log file.

The script prevents restoration directly over the original source site, `crm-task1.localhost`.

### MariaDB Compatibility Adjustment

During testing, the database backup contained a `NOTE_VERBOSITY` statement that was incompatible with the MariaDB 10.8.8 environment.

To resolve this, the script creates a temporary corrected SQL backup by removing that statement before restoration.

The original backup remains unchanged.

## 11. Commands Used

Run these commands from the `task2-backup-restore` folder in Windows PowerShell.

### Check available options

```powershell
python backup.py --help
```

### Create a backup

```powershell
python backup.py backup
```

### Verify the latest backup

```powershell
python backup.py verify
```

### Verify a specific backup

```powershell
python backup.py verify --timestamp 20261107_203706
```

### Apply retention policy

```powershell
python backup.py retention
```

### Restore a backup to a test site

```powershell
python backup.py restore --timestamp 20261107_203706 --target-site crm-restore-cli.localhost
```

### Check Python syntax

```powershell
python -m py_compile backup.py
```

## 12. Testing and Validation

The following tests were performed during implementation.

| Test | Result |
|---|---|
| Python syntax validation | Successful |
| Backup creation | Successful |
| Backup files copied locally | Successful |
| SHA-256 checksum generation | Successful |
| Backup verification | Successful |
| Retention policy execution | Successful |
| Restore confirmation prompt | Successful |
| Restore to separate test site | Successful |
| Database table verification | Successful |
| Application version verification | Successful |
| Logging | Successful |

### Restore Validation

The automated restore was tested using:

`crm-restore-cli.localhost`

The restored site was checked using Frappe Bench:

```bash
bench --site crm-restore-cli.localhost list-apps
```

Expected application output from the test:

```text
frappe  15.126.0  version-15
crm     1.92.0    main
```

The database was also checked to confirm that important Frappe tables existed.

Example MariaDB commands:

```sql
SHOW TABLES LIKE 'tabDocType';
SHOW TABLES LIKE 'tabSingles';
SHOW TABLES LIKE 'tabUser';

SELECT COUNT(*) FROM tabDocType;
```

The restored database contained 329 records in the `tabDocType` table during testing.

## 13. Logging and Error Handling

The project maintains a `backup.log` file to record important activities.

The log includes:

- Backup creation status
- Checksum verification results
- Retention policy execution
- Restore operation status
- Errors encountered during execution

The script also handles errors such as missing backup files, checksum mismatches, and failed Docker or Bench commands.

## 14. Challenges Faced and Solutions

| Challenge | Solution |
|---|---|
| Database backup contained an incompatible SQL statement | Created a temporary corrected SQL copy before restoration. |
| Interactive database password prompt failed initially | Updated command execution to support interactive Docker terminal access. |
| Backup integrity needed validation | Implemented SHA-256 checksum generation and verification. |
| Old backups could accumulate | Implemented a seven-backup retention policy inside the container. |
| Source site data needed protection | Tested restoration using a separate test site instead of the original site. |

## 15. Conclusion

This project demonstrates how Python can automate backup and recovery operations for a Frappe CRM application running in Docker.

It combines Frappe Bench, Docker, MariaDB, SHA-256 verification, retention management, and logging into a command-line automation tool.

The implementation was tested by creating backups, verifying their integrity, applying the retention policy, and successfully restoring a backup to a separate test site.

**Project:** Frappe CRM – Python Backup & Restore Automation Tool  
**Task:** Task 2 – DevOps Internship  
**Primary Language:** Python  
**Environment:** Docker, Frappe Bench, MariaDB
**Branch:** Task2-Shirisha-Thakur