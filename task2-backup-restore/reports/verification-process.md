\# Checksum Verification Process



\## Objective



To verify the integrity of backup files and ensure they have not been modified or corrupted.



\## Verification Workflow



1\. Python reads the checksum manifest (`checksum\_manifest.json`).

2\. The script identifies the backup files associated with the selected timestamp.

3\. It calculates a new SHA-256 checksum for each file.

4\. The calculated checksum is compared with the stored checksum.

5\. If all checksums match, verification succeeds.

6\. If a file is missing or its checksum differs, verification fails.



\## What is SHA-256?



SHA-256 (Secure Hash Algorithm 256-bit) is a cryptographic hashing algorithm that generates a unique 64-character hexadecimal value from file contents.



Even a small change in a file produces a different checksum.



\## What is a Checksum Manifest?



A checksum manifest is a JSON file containing backup filenames and their SHA-256 values.



It provides the reference values used during verification.



\## Command



```powershell

python scripts/backup.py verify --timestamp 20261107\_203706

