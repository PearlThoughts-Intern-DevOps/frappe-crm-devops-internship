\# Backup Process



\## Objective

To create a complete backup of the Frappe CRM site and store a persistent copy on the Windows host.



\## Backup Workflow



1\. Python executes the Frappe Bench backup command inside the Docker container.

2\. The `--with-files` option includes database, public files and private files.

3\. The generated backup files are copied from the container to the local backups directory.

4\. Python calculates the SHA-256 checksum of each backup file.

5\. A checksum manifest is generated in JSON format.

6\. The operation is recorded in the application log.



\## Command Used



```bash

bench --site crm-task1.localhost backup --with-files

