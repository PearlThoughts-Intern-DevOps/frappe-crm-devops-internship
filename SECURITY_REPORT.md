# DevSecOps Security Report: Frappe CRM

Author: yourname | Date: 2026-11-19

## 1. What is DevSecOps and why scan?
DevSecOps adds security checks to every stage of the DevOps pipeline (code, build, deploy) instead of only at the end. Problems found early are cheaper to fix. Images and libraries carry known CVEs, leaked secrets give direct access to systems, and misconfigured Docker/Kubernetes files widen the damage of any breach.

## 2. Tools used
| Area | Tool | Checks |
|---|---|---|
| Docker images | Trivy | OS packages and libraries in images |
| Dependencies | Trivy fs | package.json, yarn.lock, requirements |
| Secrets | Gitleaks | Keys, tokens, passwords in code and git history |
| Code (SAST) | Semgrep | Insecure code patterns |
| Docker/K8s config | Checkov | Dockerfile and Kubernetes misconfigurations |

All run automatically in `.github/workflows/security.yml` (GitHub Actions).

## 3. Findings summary
| Source | Critical | High | Medium | Low |
|---|---|---|---|---|
| Docker images | | | | |
| Dependencies | | | | |
| Secrets (Gitleaks) | | | | |
| Checkov | | | | |

## 4. Key findings and solutions
| Severity | Finding | Where | Solution |
|---|---|---|---|
| Critical | | | |
| High | | | |
| Medium | | | |
| Low | | | |

## 5. Common solutions
- Image CVEs: use newer or slimmer base images, rebuild often, pin versions.
- Dependency CVEs: upgrade to the Fixed Version Trivy lists.
- Secrets: revoke and rotate, remove from code and history, use env vars or Secrets.
- Dockerfile: add non-root USER and HEALTHCHECK, avoid latest tags.
- Kubernetes: runAsNonRoot, readOnlyRootFilesystem, no privilege escalation, resource limits, probes.

## 6. Conclusion
(2-3 lines: total issues, biggest risks, what will be fixed.)
