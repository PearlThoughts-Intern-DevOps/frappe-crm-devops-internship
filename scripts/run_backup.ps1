<#
.SYNOPSIS
    Frappe CRM Backup & Restore Automation Tool — Windows PowerShell Launcher
.DESCRIPTION
    Launches the Python-based Backup and Restore tool either natively or via Docker.
.EXAMPLE
    .\run_backup.ps1 backup --site crm.localhost
    .\run_backup.ps1 list --site crm.localhost
    .\run_backup.ps1 verify --site crm.localhost
    .\run_backup.ps1 restore --source-site crm.localhost --target-site test.localhost
#>

[CmdletBinding()]
param(
    [Parameter(ValueFromRemainingArguments = $true)]
    [string[]]$ScriptArgs
)

$ContainerName = "crm-frappe-1"
$LocalScript = Join-Path $PSScriptRoot "frappe_backup_manager.py"
$DockerScript = Join-Path (Split-Path $PSScriptRoot -Parent) "docker\scripts\frappe_backup_manager.py"

# Sync file to docker/scripts to ensure latest version is mounted
if (Test-Path $LocalScript) {
    Copy-Item -Path $LocalScript -Destination $DockerScript -Force -ErrorAction SilentlyContinue
}

# Check if docker is running and container exists
$ContainerRunning = docker ps --format "{{.Names}}" 2>$null | Select-String -Pattern "^$ContainerName$"

if ($ContainerRunning) {
    Write-Host "[INFO] Executing backup tool inside Docker container '$ContainerName'..." -ForegroundColor Cyan
    docker exec -it $ContainerName python /workspace/scripts/frappe_backup_manager.py @ScriptArgs
} else {
    Write-Host "[INFO] Attempting local python execution..." -ForegroundColor Cyan
    python $LocalScript @ScriptArgs
}

