# Task 2: Frappe CRM Backup and Restore

## What I worked on

For this task, I made a small Python tool to back up my local Frappe CRM site,
check that the backup files have not changed, keep older automated backups
under control, and test a restore on a separate site.

I kept the backups outside the project folder, under:

```text
%USERPROFILE%\FrappeCRMBackups\crm_localhost\
```

This keeps database and customer files out of Git. The backup folder should
still be treated as sensitive data.

## Architecture

```text
Windows PowerShell
       |
       | python .\backup_tool.py <command>
       v
backup_tool.py
       |
       | Docker Compose commands
       v
Frappe container (Bench) -------- MariaDB 10.8
       |                                  |
       | bench backup --with-files        | site database
       v                                  |
Site backup files in container            |
       |                                  |
       | docker compose cp                |
       v                                  |
Windows backup folder                     |
       |
       +--> Make copied SQL dump compatible with MariaDB 10.8
       +--> Write manifest.json (file names, sizes, SHA-256)
       +--> Verify hashes and sizes
       +--> Keep the newest seven timestamped automated sets
       |
       | restore command: verify first,
       | then stage files and restore only to a new test site
       v
test_<name>.localhost
```

The normal CRM site is `crm.localhost`. The restore command checks the target
name and refuses to restore over that site or an existing site. This let me
test the backup on `test_restore3.localhost` instead of risking the working
site.

## What the backup contains

Bench creates these four backup files:

1. A compressed database dump (`*-database.sql.gz`)
2. The public files archive (`*-files.tar`)
3. The private files archive (`*-private-files.tar`)
4. The site configuration backup (`*-site_config_backup.json`)

After copying them to the Windows backup folder, the tool writes a
`manifest.json`. For each file, it records the file name, size, and SHA-256
hash. The verify command checks those values against the files on disk.

## MariaDB compatibility issue

My Docker setup used MariaDB 10.8.8 for the server, but the Frappe container's
`mariadb-dump` was version 11.8.6. The dump contained two `NOTE_VERBOSITY`
statements that the older server did not support. My first restore attempt
failed with an unknown system variable error.

I updated the tool to remove those two statements from the copied compressed
SQL dump before creating its manifest. It checks that exactly two matching
statements were found; if not, it reports an error instead of silently
continuing. The original Bench dump and the older manual backup are not
rewritten. I tested this change on a temporary copy first.

## Commands I used

Run these from the project folder in PowerShell:

```powershell
# Create a backup, write and verify its manifest, then apply retention
python .\backup_tool.py backup

# Verify the newest backup
python .\backup_tool.py verify

# Verify a particular backup
python .\backup_tool.py verify --backup-id 20261104_203809_300675

# List backup sets and their verification status
python .\backup_tool.py list-backups

# Restore a verified backup to a separate test site
python .\backup_tool.py restore `
  --target-site test_restore3.localhost `
  --backup-id 20261104_203809_300675
```

## How I tested it

- I checked that the Docker services were running and reviewed the Bench
  backup and restore commands.
- I ran the backup tool and created automated backup
  `20261104_203809_300675`.
- The tool wrote the manifest and verified the backup. I also ran
  `verify --backup-id 20261104_203809_300675` separately, and it passed.
- I tested the MariaDB compatibility change on a temporary copy so the
  original backup was not changed.
- I tested retention using temporary folders. It removed only the oldest
  timestamped automated set, kept seven automated sets, and left the `_manual`
  folder alone.
- I restored backup `20261104_203809_300675` to
  `test_restore3.localhost`. The restore completed, the website loaded, and
  `bench --site test_restore3.localhost list-apps` showed Frappe 15.126.0 and
  CRM 1.92.0.

## Issues and limitations I found

- The older manual set `20261104_131547_manual` has a SHA-256 mismatch for its
  database dump. The tool reports it as invalid. I did not change its manifest
  to make it appear valid, and it should not be used as a verified backup.
- `test_restore.localhost` and `test_restore2.localhost` are incomplete from
  the earlier restore attempts. I left them in place. The successful restore
  is `test_restore3.localhost`.
- Retention was tested using temporary folders. I did not use that test to
  delete real backup sets.

## Safety reminders

- Do not restore over `crm.localhost`.
- Keep backup archives out of Git and do not share them publicly.
- The database and private files may contain sensitive CRM data.
- The local Compose passwords are for development and must not be used for a
  production deployment.
