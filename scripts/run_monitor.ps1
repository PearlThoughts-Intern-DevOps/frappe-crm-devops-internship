<#
.SYNOPSIS
    Frappe CRM Docker Monitoring & Auto-Recovery Tool — Windows PowerShell Launcher
.DESCRIPTION
    Launches the Python-based Docker monitoring and auto-recovery tool with automated
    Python runtime discovery and Docker environment validation.
.EXAMPLE
    .\run_monitor.ps1
    .\run_monitor.ps1 --output-json scripts/samples/system_health_report_sample.json
    .\run_monitor.ps1 --auto-restart --dry-run
    .\run_monitor.ps1 --auto-restart
    .\run_monitor.ps1 --watch --interval 5
#>

[CmdletBinding()]
param(
    [Parameter(ValueFromRemainingArguments = $true)]
    [string[]]$ScriptArgs
)

$ScriptDir = $PSScriptRoot
$LocalScript = Join-Path $ScriptDir "frappe_docker_monitor.py"
$DockerScript = Join-Path (Split-Path $ScriptDir -Parent) "docker\scripts\frappe_docker_monitor.py"

# Sync file to docker/scripts to ensure latest version is available in docker workspace
if (Test-Path $LocalScript) {
    Copy-Item -Path $LocalScript -Destination $DockerScript -Force -ErrorAction SilentlyContinue
}

# Resolve Python Executable
$PythonExe = $null

# 1. Check Python 3.12 default install location
$KnownPython = "$env:LOCALAPPDATA\Programs\Python\Python312\python.exe"
if (Test-Path $KnownPython) {
    $PythonExe = $KnownPython
}

# 2. Check py launcher
if (-not $PythonExe) {
    $PyCmd = Get-Command py.exe -ErrorAction SilentlyContinue
    if ($PyCmd) {
        $PythonExe = $PyCmd.Source
    }
}

# 3. Check python in PATH
if (-not $PythonExe) {
    $PyCommand = Get-Command python.exe -ErrorAction SilentlyContinue
    if ($PyCommand -and ($PyCommand.Source -notmatch "WindowsApps")) {
        $PythonExe = $PyCommand.Source
    }
}

if (-not $PythonExe) {
    Write-Error "Python runtime not detected. Please install Python 3.10+ or ensure it is added to your PATH."
    exit 2
}

# Set PYTHONPATH to scripts directory
$env:PYTHONPATH = $ScriptDir

# Execute monitor script with arguments
& $PythonExe $LocalScript @ScriptArgs
exit $LASTEXITCODE

