# DevSecOps Security Scanning

## Overview

This task demonstrates security scanning of the Frappe CRM project using Trivy, Gitleaks and Checkov.

The objective is to identify vulnerabilities in Docker images and application dependencies, detect potential exposed secrets, and validate Kubernetes manifests against security best practices.

## Tools

- **Trivy:** Vulnerability scanning for container images and dependencies.
- **Gitleaks:** Secret detection in repository contents.
- **Checkov:** Security and compliance scanning for Kubernetes configurations.

## Project Structure

```text
security-scan/
├── k8s-manifest/
│   ├── frappe.yaml
│   ├── mariadb.yaml
│   ├── namespace.yaml
│   ├── redis.yaml
│   └── secret.yaml
├── reports/
│   ├── SUMMARY.md
│   ├── checkov.txt
│   ├── trivy-dependencies.txt
│   └── images-found.txt
├── REPORT.md
├── README.md
└── scan.sh
```

## Scan Coverage

| Component | Tool | Purpose |
|---|---|---|
| Docker images | Trivy | Identify OS and package vulnerabilities |
| Application dependencies | Trivy | Identify vulnerable dependencies |
| Git repository | Gitleaks | Detect potential exposed secrets |
| Kubernetes manifests | Checkov | Identify configuration security issues |

## Running the Scans

Make the script executable:

```bash
chmod +x scan.sh
```

Execute:

```bash
./scan.sh
```

The script runs the configured security scans and saves the generated reports in the reports directory.

**Prerequisites:** Docker and the required scanning tools must be installed and accessible in the execution environment.

## Reports

- `SUMMARY.md` – Summary of scan findings.
- `checkov.txt` – Checkov configuration scan output.
- `trivy-dependencies.txt` – Trivy dependency scan output.
- `images-found.txt` – Docker images identified for scanning.
- `REPORT.md` – Consolidated findings, observations and recommended remediation.

## Important Notes

- Scan results are point-in-time findings and may change as vulnerability databases are updated.
- Validate findings before applying dependency or image upgrades.
- Never commit actual credentials, API keys, tokens or unredacted secret scan reports.
- Review Kubernetes Secret manifests before committing them.

## Conclusion

This task demonstrates the use of security scanning tools as part of a DevSecOps workflow to identify and document potential security risks before deployment.