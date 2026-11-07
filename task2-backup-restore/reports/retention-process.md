\# Backup Retention Policy



\## Objective



To manage backup storage by retaining only the latest seven backup sets inside the Frappe Docker container.



\## What Is a Retention Policy?



A retention policy defines how long backup files should be kept and when older backups should be removed.



It helps control storage usage and prevents unnecessary accumulation of backup files.



\## Retention Workflow



1\. Python executes a command inside the Frappe Docker container.

2\. The script identifies database backup files using the site-specific filename pattern.

3\. Backup filenames are sorted in reverse chronological order.

4\. The latest seven backup sets are retained.

5\. Older backup sets are identified using their timestamps.

6\. All files belonging to each older backup set are deleted.

7\. The operation is recorded in the application log.



\## Retention Configuration



The current retention limit is:



\*\*7 backup sets\*\*



\## Command



```powershell

python scripts/backup.py retention

