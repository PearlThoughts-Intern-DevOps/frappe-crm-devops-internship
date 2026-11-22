# DevSecOps Security Assessment Report — Frappe CRM

**Assessment date:** November 2026
**Project:** Frappe CRM
**Assessment type:** DevSecOps security scanning
**Status:** Scans completed; findings require remediation and review.

---

## 1. Objective

The objective was to assess the security of the Frappe CRM project by scanning Docker images, software dependencies, Git history, current source files, and Kubernetes manifests.

The assessment used automated tools to identify potential vulnerabilities, exposed credentials, and insecure configuration.

## 2. Tools and versions

| Tool | Version |
|---|---|
| Trivy | 0.76.2 |
| Gitleaks | 8.30.1 |
| Checkov | 3.4.6 |
| Docker | 29.9.2 |

## 3. Trivy — Docker image vulnerability scanning

The following images were scanned:

- `mariadb:10.8`
- `redis:alpine`
- `frappe/bench:latest`

### 3.1 Results

| Docker image | Critical | High | Medium | Low | Unknown | Total |
|---|---:|---:|---:|---:|---:|---:|
| mariadb:10.8 | 5 | 83 | 410 | 163 | 1 | 662 |
| redis:alpine | 0 | 0 | 1 | 0 | 0 | 1 |
| frappe/bench:latest | 13 | 935 | 1,479 | 1,369 | 46 | 3,842 |

These are scanner-reported vulnerability records. Counts across different images should not be interpreted as unique CVEs because the same vulnerability may occur in multiple packages or images.

### 3.2 Recommendations

1. Review Critical and High vulnerabilities first.
2. Identify available fixed versions for affected packages.
3. Update vulnerable base images and packages using a tested build process.
4. Test updated images before deployment.
5. Replace mutable `latest` image references with tested version tags or image digests.
6. Re-scan images after remediation.

## 4. Trivy — Dependency scanning

Trivy filesystem scanning detected three language-specific dependency files.

### Results

| Severity | Findings |
|---|---:|
| Critical | 0 |
| High | 43 |
| Medium | 33 |
| Low | 21 |
| **Total** | **97** |

### Recommendations

- Review vulnerable direct and transitive dependencies.
- Update packages to secure compatible versions.
- Introduce and maintain dependency lockfiles where appropriate.
- Re-run dependency scans after updates.
- Test application compatibility before merging dependency changes.

**Limitation:** Seven dependency manifest files were identified during repository discovery, but Trivy detected only three language-specific files in this scan. The result therefore does not establish that every manifest or dependency was fully assessed. Development and testing dependencies were suppressed by default.

## 5. Gitleaks — Secret scanning

### 5.1 Git history scan

The completed Git history scan examined:

- 6,273 commits
- Approximately 42.71 MB of Git history
- PDF files excluded because Gitleaks could not process an encountered PDF

**Finding:**

| Rule | File | Line | Result |
|---|---|---:|---|
| generic-api-key | `crm/twilio/api.py` | 96 | 1 potential credential exposure |

The historical file contains Twilio-related credentials, including an account SID, application SID, and authentication token.

**Risk: High — credential exposure**

Recommended remediation:

1. Notify the repository or Twilio account owner.
2. Rotate the exposed authentication token.
3. Store credentials in environment variables or a secrets manager.
4. Remove hardcoded credentials from the current source if present.
5. Review Git history cleanup with the repository owner. Deleting a credential from the latest file does not remove historical exposure.

Credential values are intentionally excluded from this report.

### 5.2 Current source directory scans

| Directory | Result |
|---|---|
| `crm` | No leaks found |
| `frontend` | No leaks found |
| `frappe-ui` | No leaks found |

No secrets were detected in these three separately scanned application source directories.

### 5.3 Repository-wide directory scan

The initial repository-wide scan reported 38 findings.

Manual classification of the reported locations:

| Finding location | Count | Assessment |
|---|---:|---|
| Generated Trivy Frappe Bench JSON report | 32 | Likely false positives; generated package metadata |
| Generated Trivy MariaDB JSON report | 5 | Generic API-key matches in generated scan data |
| Local recovery backup configuration | 1 | Sensitive database password |

The 32 Sourcegraph rule matches and five generic API-key matches occurred in generated Trivy JSON reports, not in the separately scanned application source directories.

The recovery backup file is:

`docker/recovery-backup/crm.localhost/site_config.json`

It contains a non-empty `db_password` field. The file was confirmed as not Git-tracked and is excluded through `.git/info/exclude`.

**Risk: Medium to High, depending on whether the password is active or reused.**

Recommended remediation:

- Keep the recovery backup private and access-restricted.
- Rotate the database password if it is active or exposed elsewhere.
- Continue excluding recovery backups and sensitive configuration from version control.
- Avoid sharing backup contents in logs, reports, or pull requests.

The 38 directory-scan findings should not be reported as 38 confirmed credential leaks.

## 6. Checkov — Kubernetes security scanning

Kubernetes manifests were scanned from the separate local project:

`Frappe-crm-kubernetes-repo`

### 6.1 Scan summary

| Result | Count |
|---|---:|
| Passed checks | 738 |
| Failed checks | 154 |
| Skipped checks | 0 |
| Total check results | 892 |
| Unique failed policy IDs | 40 |

The 154 failures represent failed policy evaluations, not necessarily 154 unique vulnerabilities.

### 6.2 Important findings

| Policy ID | Finding | Affected configuration | Suggested risk |
|---|---|---|---|
| CKV_K8S_21 | Workloads use the default namespace | Kubernetes manifests | Medium |
| CKV_K8S_39 | Containers may have `CAP_SYS_ADMIN` capability | Redis, workers and websocket workloads | High |
| CKV_K8S_12 | Memory requests are not defined | Application workloads | Medium |
| CKV2_K8S_6 | Pods do not have associated NetworkPolicies | Multiple workloads | High |

Risk classifications above are assessment priorities, not official Checkov severity ratings.

### 6.3 Recommendations

1. Deploy application workloads in a dedicated namespace instead of the default namespace.
2. Remove unnecessary Linux capabilities, especially `CAP_SYS_ADMIN`.
3. Define CPU and memory requests and appropriate limits.
4. Implement Kubernetes NetworkPolicies that allow only required communication.
5. Review pod security contexts and privilege settings.
6. Re-run Checkov after approved configuration changes.

Some failed checks may concern cluster-level configuration that cannot be verified from application manifests alone. Those checks require separate infrastructure-level review.

## 7. Docker Compose and Dockerfile scan limitations

- The repository's Compose configuration was checked using Checkov's generic YAML framework because the installed Checkov version did not support a `docker_compose` framework.
- The Compose scans returned no detailed pass/fail summary. They must not be interpreted as successful security validation.
- No Dockerfile was found in the repository during the scan preparation. Therefore, a dedicated Dockerfile security scan was not applicable.

## 8. Overall risk assessment

| Area | Main observation | Priority |
|---|---|---|
| Docker images | Critical and High vulnerability records in MariaDB and Frappe Bench images | Critical |
| Dependencies | 43 High vulnerability records | High |
| Git history | Twilio authentication credential exposure | High |
| Local backup | Non-empty database password in local recovery backup | Review and rotate if active |
| Kubernetes | Privileged capability and missing NetworkPolicy checks | High |
| Current application source | No leaks found in CRM, frontend or Frappe UI scans | No findings |

## 9. Recommended remediation order

1. Notify the repository owner and rotate the exposed Twilio authentication token.
2. Verify and rotate the recovery backup database password if it is active or reused.
3. Review Critical and High image vulnerabilities and prepare tested image updates.
4. Review the 43 High dependency findings and update affected packages.
5. Remove unnecessary privileged capabilities and implement NetworkPolicies.
6. Address namespace and resource-request configuration findings.
7. Repeat all applicable scans and compare results with the original reports.

## 10. Assessment limitations

- Image and dependency vulnerability counts are scanner-reported records and may include overlapping vulnerabilities.
- Trivy dependency scanning detected only three language-specific files.
- Gitleaks Git history scanning excluded PDF files.
- Repository-wide Gitleaks findings included generated JSON reports and a local backup; they were not all confirmed secrets.
- Checkov's Kubernetes failures require manual triage, especially checks involving cluster-level settings.
- Compose scans did not produce detailed summaries.
- No production deployment, credential rotation, or application-code remediation was performed as part of this assessment.

## 11. Conclusion

The assessment identified important security issues in container images, dependencies, Git history, and Kubernetes configuration.

The most urgent issue is the historical Twilio credential exposure. The image and dependency vulnerability findings also require prioritised review and remediation.

The CRM, frontend, and Frappe UI source directory scans reported no exposed secrets. However, this does not eliminate the historical credential exposure or the sensitive local recovery backup.

This report records the initial security assessment. Remediation and subsequent verification scans are required before the project can be considered secure.
