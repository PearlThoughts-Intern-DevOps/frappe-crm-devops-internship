# DevSecOps Security Report: Frappe CRM

Author: yourname | Date: 2026-11-19

## 1. What is DevSecOps and why scan?
DevSecOps adds security checks to every stage of the DevOps pipeline (code, build, deploy) instead of only at the end. Problems found early are cheaper to fix. Images and libraries carry known CVEs, leaked secrets give direct access to systems, and misconfigured Docker/Kubernetes/CI files widen the damage of any breach.

## 2. Tools used
| Area | Tool | Checks |
|---|---|---|
| Docker images | Trivy (image) | OS packages and libraries inside images |
| Dependencies | Trivy (fs) | yarn.lock / package files |
| Secrets | Gitleaks | Keys, tokens, passwords in code and git history |
| Code (SAST) | Semgrep | Insecure code patterns, CI and Terraform config |
| Docker/K8s config | Checkov | Dockerfile and Kubernetes misconfigurations |

All run automatically in `.github/workflows/security.yml` (GitHub Actions) on every push and PR.

## 3. Findings summary
| Source | Critical | High | Medium | Low |
|---|---|---|---|---|
| Docker images (frappe/bench, mariadb:10.6, redis:alpine) | 13 | 796 | 1157 | 1320 |
| Dependencies (Trivy fs, yarn.lock) | 0 | 43 | not counted | not counted |
| Semgrep code/config (231 findings) | 0 | 0 | 231 (ERROR/WARNING) | 0 |
| Secrets (Gitleaks) | see note | | | |
| Checkov (Docker/K8s) | see GitHub run summary | | | |

Note: Gitleaks first failed because the action needs a license for organization repos; it was switched to the free Docker version.

Per-image results:
| Image | Critical | High | Medium | Low |
|---|---|---|---|---|
| frappe/bench:latest | 12 | 771 | 1082 | 1294 |
| mariadb:10.6 | 1 | 25 | 74 | 26 |
| redis:alpine | 0 | 0 | 1 | 0 |

## 4. Key findings and solutions
| Severity | Finding | Where | Solution |
|---|---|---|---|
| Critical | 13 critical CVEs in OS packages | frappe/bench:latest (12), mariadb:10.6 (1) | Rebuild on a newer base image, run apt upgrade, move off the old mariadb 10.6 |
| High | 796 high CVEs in OS packages | frappe/bench:latest (771), mariadb:10.6 (25) | Same as above; use slimmer images and pin versions |
| High | 43 vulnerable npm packages, e.g. vite 8.2.0, ws, nanoid, postcss, brace-expansion, fast-uri, markdown-it, linkify-it, socket.io-parser, @tiptap/core, @vue/server-renderer | frontend/yarn.lock, frappe-ui/yarn.lock | Upgrade to the Fixed Version in the Trivy output (e.g. vite 8.3.3, ws 8.21.0, postcss 8.5.18, nanoid 3.3.18) and re-run yarn install |
| Medium | GitHub Actions use mutable tags and some steps are open to shell injection | .github/workflows/*, .github/actions/* | Pin actions to a full commit SHA; pass untrusted inputs through env vars instead of inline in `run:` |
| Medium | v-html used on dynamic content (XSS risk) | frontend/src/components/Activities/*, Modals/*, Notifications.vue | Sanitize HTML (e.g. DOMPurify) or use text binding |
| Medium | docker-compose services without no-new-privileges and with writable filesystem | .devcontainer/docker-compose.yml | Add `security_opt: [no-new-privileges:true]` and `read_only: true` where possible |
| Medium | Subnet assigns public IPs; RDS has no logging enabled | terraform/main.tf | Set `map_public_ip_on_launch = false`; enable RDS log exports |
| Low | Path traversal via path.join, non-literal RegExp, child_process use | frappe-ui build and migration scripts | Validate inputs; these run in dev tooling so risk is low; escape user input in RegExp |
| Low | 1320 low CVEs in OS packages | all images | Fixed by regular image rebuilds |

## 5. Common solutions
- Image CVEs: update base images, rebuild regularly, remove unused packages, scan in CI.
- Dependency CVEs: upgrade to the Fixed Version, use Dependabot or Renovate.
- Secrets: revoke and rotate, remove from code and history, use env vars or Secrets.
- CI/CD: pin actions by SHA, least-privilege permissions.
- Docker/Kubernetes: non-root user, read-only filesystem, no privilege escalation, resource limits, probes.

## 6. Conclusion
The pipeline found 13 critical and 839 high issues, most from large base images (frappe/bench) and outdated npm packages. Upgrading base images and the listed packages would remove most of the critical and high findings. Because the gate is strict, the pipeline fails until these are fixed, which is the intended behaviour of a DevSecOps gate.
