\# Backup Restoration Process



\## Objective



To restore a Frappe CRM site using a previously generated and verified backup.



\## What Is Restoration?



Restoration is the process of recovering application data and files from a backup when required.



\## Restore Workflow



1\. The user selects a backup timestamp and target site.

2\. Python verifies the backup using its SHA-256 checksum manifest.

3\. The script checks that the required database and file backups exist.

4\. The user must confirm the operation by typing `RESTORE`.

5\. Backup files are copied into a temporary directory inside the Frappe Docker container.

6\. The script prepares a MariaDB-compatible copy of the SQL backup by removing the incompatible `NOTE\_VERBOSITY` statement.

7\. Frappe Bench restores the database, public files and private files to the target site.

8\. The operation is recorded in the application log.



\## Important Safety Check



The script prevents restoration over the original source site:



`crm-task1.localhost`



Restoration must use a separate target site to protect the original application and its data.



\## Command



```powershell

python scripts/backup.py restore --timestamp 20261107\_203706 --target-site crm-restore-cli.localhost

