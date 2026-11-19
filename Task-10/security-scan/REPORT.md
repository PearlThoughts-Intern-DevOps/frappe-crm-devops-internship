# DevSecOps Security Scanning Report

## 1. Overview

This task explores DevSecOps security scanning by identifying vulnerabilities in container images, application dependencies, exposed secrets and Kubernetes configuration files.

The objective is to identify security weaknesses early in the development lifecycle and document appropriate remediation measures.

## 2. Tools Used

| Tool | Purpose |
|---|---|
| Trivy | Container image and dependency vulnerability scanning |
| Gitleaks | Detection of potential exposed secrets |
| Checkov | Infrastructure and Kubernetes configuration security scanning |

## 3. Scan Scope

The following components were scanned:

- Frappe Bench Docker image
- MariaDB Docker images (10.6 and 10.8)
- Redis Alpine Docker image
- Application dependency lock files
- Git repository for potential exposed secrets
- Kubernetes manifests for Frappe, MariaDB and Redis

## 4. Trivy – Container Image Scan Results

| Image | Critical | High | Medium | Low |
|---|---:|---:|---:|---:|
| frappe/bench:latest | 12 | 771 | 1,075 | 1,294 |
| mariadb:10.6 | 1 | 26 | 73 | 26 |
| mariadb:10.8 | 5 | 84 | 409 | 163 |
| redis:alpine | 0 | 0 | 1 | 0 |

### Observations

- Frappe Bench had the highest number of reported vulnerabilities.
- MariaDB images contained vulnerabilities in operating-system packages and Go standard library components.
- Redis Alpine had one medium-severity finding.
- Some critical findings did not have fixes available at the time of scanning.

### Recommended Actions

- Review and update outdated base images and system packages.
- Apply compatible security updates when fixes become available.
- Rebuild images and rerun Trivy after remediation.
- Review vulnerabilities for actual package usage and exposure before prioritizing remediation.

## 5. Trivy – Dependency Scan Results

The following dependency lock files were scanned:

- `frappe-ui/yarn.lock`
- `frontend/yarn.lock`
- `yarn.lock`

| Severity | Findings |
|---|---:|
| Critical | 0 |
| High | 45 |
| Medium | 33 |
| Low | 19 |
| **Total** | **97** |

### Sample Findings

| Package | Severity | Installed Version | Example Fixed Version |
|---|---|---|---|
| @tiptap/core | High | 3.26.0 | 3.30.5 |
| dompurify | High | 3.4.5 | 3.4.17 |
| linkify-it | High | 5.0.0 | 5.0.2 |
| markdown-it | High | 14.1.1 | 14.3.3 |
| nanoid | High | 3.3.12 | 3.3.18 |
| postcss | High | 8.5.15 | 8.5.18 |
| prosemirror-view | High | 1.41.8 | 1.42.3 |

### Recommended Actions

- Review vulnerable direct and transitive dependencies.
- Check compatibility before upgrading package versions.
- Regenerate lock files after approved dependency updates.
- Rerun Trivy to verify remediation.

## 6. Gitleaks – Secret Detection

Gitleaks reported **3 potential secret findings**.

The reported locations included:

- `kubernetes/02-secret.yaml.example`
- `crm/twilio/api.py`

These findings require manual validation to determine whether they represent actual credentials or false positives.

### Recommended Actions

- Inspect flagged locations without exposing secret values.
- Replace hardcoded credentials with Kubernetes Secrets or a suitable secret-management solution.
- Rotate credentials if any real secret has been exposed.
- Avoid committing raw Gitleaks reports that may contain sensitive values.

## 7. Checkov – Kubernetes Configuration Scan

Checkov scanned 11 resources.

| Result | Count |
|---|---:|
| Passed | 226 |
| Failed | 45 |
| Skipped | 0 |
| Parsing errors | 0 |

### Key Areas Identified for Improvement

- Container and pod security contexts
- Running containers as non-root users
- Privilege escalation restrictions
- Linux capability restrictions
- Seccomp configuration
- Read-only filesystem configuration
- Liveness probes
- Image digest pinning
- Kubernetes NetworkPolicies
- Service account token mounting

### Recommended Actions

- Apply least-privilege security settings.
- Restrict unnecessary Linux capabilities and privilege escalation.
- Use non-root containers wherever supported.
- Review NetworkPolicies to restrict unnecessary network access.
- Configure health probes and image references appropriately.
- Validate storage requirements before enabling read-only root filesystems.

## 8. Overall Findings

The scans identified vulnerabilities across container images and application dependencies, potential secret exposure, and Kubernetes configuration weaknesses.

The most significant areas requiring review are:

1. Critical and high vulnerabilities in the Frappe Bench and MariaDB images.
2. High-severity application dependency findings.
3. Potential exposed credentials identified by Gitleaks.
4. Kubernetes security configuration gaps identified by Checkov.

## 9. Conclusion

This exercise demonstrated how Trivy, Gitleaks and Checkov can be integrated into a DevSecOps workflow to identify security issues across application dependencies, container images, repository contents and Kubernetes configurations.

The scan results provide a baseline for prioritizing security improvements. Findings should be validated, remediated where appropriate, and rescanned to confirm that the changes are effective.

**Note:** The findings represent scanner output at the time of execution. They do not independently confirm that every reported vulnerability is exploitable in the deployed environment.