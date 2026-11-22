# Gitleaks Secret Scan Evidence

## Scope
- Scanner: Gitleaks 8.30.1
- Git history scan: 6,273 commits scanned.
- Current source directories: `crm/`, `frontend/`, and `frappe-ui/`.
- Kubernetes manifests scanned separately before submission.

## Results

| Scan | Result |
|---|---|
| Git history | 1 historical credential finding |
| `crm/` current source | No leaks found |
| `frontend/` current source | No leaks found |
| `frappe-ui/` current source | No leaks found |
| Kubernetes manifests | No leaks found |

## Historical finding

- File: `crm/twilio/api.py`
- Line: 96
- Rule: `generic-api-key`
- Finding: Twilio credential material in Git history.

The credential value is intentionally omitted.

## Recommended remediation

1. Treat the exposed credential as compromised until its owner verifies and rotates or revokes it.
2. Store replacement credentials in environment variables or an approved secret manager.
3. Ensure credentials are not committed to source control.
4. Coordinate any Git history cleanup with the repository owner. Do not rewrite shared history without approval.

## Scan limitations and handling

PDF files were excluded from the Git history scan because the scanner could not parse them.

A separate working-directory scan produced matches in generated Trivy JSON reports and a local recovery backup. These were not treated as confirmed source-code leaks. The recovery backup contains sensitive configuration and must remain local, uncommitted, and protected.
