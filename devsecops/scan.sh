#!/usr/bin/env bash
# =============================================================================
# Frappe CRM DevSecOps Automated Security Scanning Script (Bash)
# =============================================================================
# Tools: Trivy, Gitleaks, Checkov
# Scans:
#   1. Container Images (Trivy)
#   2. Repository Dependencies & SCA (Trivy FS / npm / pip)
#   3. Secrets & Credentials Detection (Gitleaks)
#   4. Infrastructure as Code (IaC) Configuration (Checkov)
# =============================================================================

set -eo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
REPORTS_DIR="${SCRIPT_DIR}/reports"

mkdir -p "${REPORTS_DIR}"

COLOR_RESET="\033[0m"
COLOR_BOLD="\033[1m"
COLOR_RED="\033[31m"
COLOR_GREEN="\033[32m"
COLOR_YELLOW="\033[33m"
COLOR_BLUE="\033[34m"
COLOR_CYAN="\033[36m"

log_info() {
    echo -e "${COLOR_BLUE}[INFO]${COLOR_RESET} $1"
}

log_success() {
    echo -e "${COLOR_GREEN}[SUCCESS]${COLOR_RESET} $1"
}

log_warn() {
    echo -e "${COLOR_YELLOW}[WARN]${COLOR_RESET} $1"
}

log_header() {
    echo ""
    echo -e "${COLOR_BOLD}${COLOR_CYAN}====================================================================${COLOR_RESET}"
    echo -e "${COLOR_BOLD}${COLOR_CYAN}  $1${COLOR_RESET}"
    echo -e "${COLOR_BOLD}${COLOR_CYAN}====================================================================${COLOR_RESET}"
}

log_header "Frappe CRM DevSecOps Security Scanner"

# --- 1. Docker Image Scanning with Trivy ---
log_header "Phase 1: Container Image Scanning (Trivy)"
IMAGES=("frappe/bench:latest" "mariadb:10.8" "redis:alpine")

for img in "${IMAGES[@]}"; do
    safe_name=$(echo "$img" | tr '/:' '-')
    log_info "Scanning container image: ${img}..."
    trivy image \
        --severity CRITICAL,HIGH,MEDIUM,LOW \
        --format json \
        -o "${REPORTS_DIR}/trivy-${safe_name}-summary.json" \
        "${img}" || true

    trivy image \
        --severity CRITICAL,HIGH \
        --format table \
        "${img}" || true
    log_success "Saved report for ${img} to ${REPORTS_DIR}/trivy-${safe_name}-summary.json"
done

# --- 2. Dependency Vulnerability Scanning (SCA) ---
log_header "Phase 2: Dependency Vulnerability Scanning (Trivy FS)"
log_info "Scanning project dependencies in ${REPO_ROOT}..."

trivy fs \
    --scanners vuln \
    --include-dev-deps \
    --severity CRITICAL,HIGH,MEDIUM,LOW \
    --format json \
    -o "${REPORTS_DIR}/trivy-dependencies-summary.json" \
    "${REPO_ROOT}" || true

trivy fs \
    --scanners vuln \
    --severity CRITICAL,HIGH \
    "${REPO_ROOT}" || true

log_success "Saved dependency SCA report to ${REPORTS_DIR}/trivy-dependencies-summary.json"

# --- 3. Secret Scanning with Gitleaks ---
log_header "Phase 3: Secret & Credential Scanning (Gitleaks)"
log_info "Running Gitleaks across repository history and working tree..."

gitleaks detect \
    --source "${REPO_ROOT}" \
    --verbose \
    --report-format json \
    --report-path "${REPORTS_DIR}/gitleaks-findings.json" \
    --exit-code 0 || {
    log_warn "Gitleaks detected potential secret exposure! Review ${REPORTS_DIR}/gitleaks-findings.json"
}

# --- 4. IaC Security Scanning with Checkov ---
log_header "Phase 4: Infrastructure as Code (IaC) Scanning (Checkov)"
if command -v checkov >/dev/null 2>&1; then
    if [ -d "${REPO_ROOT}/kubernetes" ]; then
        log_info "Scanning Kubernetes manifests with Checkov..."
        checkov -d "${REPO_ROOT}/kubernetes" \
            --framework kubernetes \
            --output json \
            --output-file-path "${REPORTS_DIR}" || true
    fi
    if [ -d "${REPO_ROOT}/terraform" ]; then
        log_info "Scanning Terraform configurations with Checkov..."
        checkov -d "${REPO_ROOT}/terraform" \
            --framework terraform \
            --output json \
            --output-file-path "${REPORTS_DIR}" || true
    fi
    if [ -d "${REPO_ROOT}/.github/workflows" ]; then
        log_info "Scanning GitHub Actions with Checkov..."
        checkov -d "${REPO_ROOT}/.github/workflows" \
            --framework github_actions \
            --output json \
            --output-file-path "${REPORTS_DIR}" || true
    fi
fi

log_header "DevSecOps Security Scanning Complete"
log_success "All security scan results have been written to ${REPORTS_DIR}"
