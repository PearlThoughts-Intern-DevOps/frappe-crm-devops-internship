Frappe CRM Backup and Restore Automation Tool

1. Overview

A Python-based automation tool for backing up and restoring a Frappe CRM site using Frappe Bench commands and Docker.

The tool supports:

* Database backups.
* Public and private file backups.
* SHA-256 checksum verification.
* Automatic retention of the latest 7 backups.
* Restoration into a separate test site.
* Logging and error handling.
* Command-line interface (CLI).

2. Requirements

* Python 3.10 or later
* Docker Desktop with WSL2 integration
* A running Frappe CRM Docker environment
* Frappe Bench installed inside the container
* Access to the MariaDB root password for restoration

No third-party Python packages are required.

3. Configuration

Edit config.json to match your environment.

Setting	Description
docker_container	Frappe application container
bench_path	Frappe Bench directory
source_site	Original CRM site
test_site	Separate restore testing site
container_backup_path	Backup directory inside container
retention_count	Number of backups to retain
backup_with_files	Include public/private files
compress_files	Compress database backup

Never store passwords or credentials in the configuration file.

4. Project Structure

backup-restore/
├── backup_tool.py
├── config.json
├── requirements.txt
├── README.md
├── backups/
├── reports/
└── logs/

5. Running the Tool

Open a terminal in the project directory.

Create a backup

python3 backup_tool.py backup

Creates a database backup and available public/private file archives, generates a manifest containing SHA-256 checksums, verifies the backup and applies retention.

Verify backups

python3 backup_tool.py verify

Checks backup files against their recorded SHA-256 checksums and generates verification reports.

List backups

python3 backup_tool.py list

Displays available backup directories.

Apply retention manually

python3 backup_tool.py cleanup

Keeps the latest 7 backups by default.

Restore a backup

python3 backup_tool.py restore BACKUP_ID

Replace BACKUP_ID with an existing backup directory name.

The tool verifies the backup before restoration and restores it into the configured test site. It requests the MariaDB root password securely through a hidden terminal prompt.

The original source site is not the restore target.

6. Backup Integrity

Each backup contains a manifest.json file.

The manifest records:

* Backup ID
* Source site
* Backup timestamp
* Backup filenames
* File sizes
* SHA-256 checksums

The verification command calculates SHA-256 again and compares it with the manifest.

A matching checksum produces PASS; a missing or modified file produces FAIL.

7. Retention Policy

The retention policy is configured through:

"retention_count": 7

After a successful backup, older backup directories beyond the configured retention count are removed.

8. Restore Safety

* Restoration is performed against a separate test site.
* The source site is not selected as the restore destination.
* Backup checksums are verified before restoration.
* MariaDB credentials are entered through hidden terminal prompts.
* A temporary compatibility-adjusted SQL archive is used for MariaDB 10.8 restoration when required.
* The original backup archive remains unchanged.

Only use the restore command with a designated test site.

9. Reports and Logs

Generated files are stored in:

* backups/ — backup archives and manifests.
* reports/ — verification reports.
* logs/ — execution logs.

10. Testing

The following operations were tested in the Frappe CRM Docker environment:

* Database and file backup creation.
* SHA-256 verification of all three backup archives.
* Backup listing.
* Restoration into crm-test.localhost.
* Application checks on both the test and original sites.

11. Security Notes

* Do not commit database passwords or other credentials.
* Keep backup archives secure because they may contain customer and application data.
* Use a separate test site for restoration.
* Do not expose backup files publicly.