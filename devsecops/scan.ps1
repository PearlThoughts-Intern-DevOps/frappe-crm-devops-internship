# =============================================================================
# Frappe CRM DevSecOps Automated Security Scanning Script (PowerShell)
# =============================================================================
# Tools: Trivy, Gitleaks, Checkov
# Scans:
#   1. Container Images (Trivy)
#   2. Repository Dependencies & SCA (Trivy FS / npm / pip)
#   3. Secrets & Credentials Detection (Gitleaks)
#   4. Infrastructure as Code (IaC) Configuration (Checkov)
# =============================================================================

[CmdletBinding()]
param(
    [string]$ReportsDir = "$PSScriptRoot\reports"
)

$ErrorActionPreference = "Continue"

Write-Host "`n====================================================================" -ForegroundColor Cyan
Write-Host "  Frappe CRM DevSecOps Security Scanner (PowerShell)" -ForegroundColor Cyan
Write-Host "====================================================================`n" -ForegroundColor Cyan

if (-not (Test-Path $ReportsDir)) {
    New-Item -ItemType Directory -Force -Path $ReportsDir | Out-Null
}

$RepoRoot = Resolve-Path "$PSScriptRoot\.."

# Update PATH
$env:PATH = [System.Environment]::GetEnvironmentVariable("PATH","Machine") + ";" + [System.Environment]::GetEnvironmentVariable("PATH","User")

# --- 1. Docker Image Scanning with Trivy ---
Write-Host "`n[PHASE 1] Container Image Scanning (Trivy)..." -ForegroundColor Yellow
$images = @("frappe/bench:latest", "mariadb:10.8", "redis:alpine")

foreach ($img in $images) {
    $safeName = $img -replace '[:/]', '-'
    Write-Host "  -> Scanning image: $img" -ForegroundColor Green
    trivy image --severity CRITICAL,HIGH,MEDIUM,LOW --format json -o "$ReportsDir\trivy-$safeName-summary.json" $img
    trivy image --severity CRITICAL,HIGH --format table $img
}

# --- 2. Dependency Vulnerability Scanning (SCA) ---
Write-Host "`n[PHASE 2] Dependency Vulnerability Scanning (Trivy FS)..." -ForegroundColor Yellow
Write-Host "  -> Scanning project dependencies in $RepoRoot" -ForegroundColor Green
trivy fs --scanners vuln --include-dev-deps --severity CRITICAL,HIGH,MEDIUM,LOW --format json -o "$ReportsDir\trivy-dependencies-summary.json" $RepoRoot
trivy fs --scanners vuln --severity CRITICAL,HIGH $RepoRoot

# --- 3. Secret Scanning with Gitleaks ---
Write-Host "`n[PHASE 3] Secret & Credential Scanning (Gitleaks)..." -ForegroundColor Yellow
Write-Host "  -> Scanning git history and repository tree..." -ForegroundColor Green
gitleaks detect --source $RepoRoot --verbose --report-format json --report-path "$ReportsDir\gitleaks-findings.json" --exit-code 0

# --- 4. IaC Security Scanning with Checkov ---
Write-Host "`n[PHASE 4] Infrastructure as Code (IaC) Scanning (Checkov)..." -ForegroundColor Yellow
$checkovCmd = Get-Command checkov -ErrorAction SilentlyContinue
if ($checkovCmd) {
    if (Test-Path "$RepoRoot\kubernetes") {
        Write-Host "  -> Scanning Kubernetes manifests..." -ForegroundColor Green
        checkov -d "$RepoRoot\kubernetes" --framework kubernetes --output json --output-file-path $ReportsDir
    }
    if (Test-Path "$RepoRoot\terraform") {
        Write-Host "  -> Scanning Terraform configurations..." -ForegroundColor Green
        checkov -d "$RepoRoot\terraform" --framework terraform --output json --output-file-path $ReportsDir
    }
    if (Test-Path "$RepoRoot\.github\workflows") {
        Write-Host "  -> Scanning GitHub Actions workflows..." -ForegroundColor Green
        checkov -d "$RepoRoot\.github\workflows" --framework github_actions --output json --output-file-path $ReportsDir
    }
}

Write-Host "`n====================================================================" -ForegroundColor Cyan
Write-Host "  DevSecOps Security Scanning Complete! Reports saved to: $ReportsDir" -ForegroundColor Cyan
Write-Host "====================================================================`n" -ForegroundColor Cyan
