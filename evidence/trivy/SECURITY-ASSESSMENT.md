# Docker Image Security Assessment

## 1. Objective

Assess the security posture of the Frappe Bench Docker image using
Trivy. Identify reported vulnerabilities, examine critical findings,
verify affected installed packages, and document recommendations.

The assessment does not modify the original Frappe CRM application
source code or the scanned Docker image.

## 2. Scan Environment

| Property | Value |
|---|---|
| Scanner | Trivy |
| Trivy version | 0.76.2 |
| Scan date | 18 November 2026 |
| Vulnerability DB version | 2 |
| Image | frappe/bench:latest |
| Operating system | Debian GNU/Linux 13.7 |
| Architecture | linux/amd64 |
| Image ID | sha256:36386e3f69d9fa323dd57c24b4314d4d73e8dba6747806aba5d32bc821e63f69 |

## 3. Vulnerability Summary

| Severity | Findings |
|---|---:|
| Critical | 12 |
| High | 750 |
| Medium | 977 |
| Low | 1,198 |
| Unknown | 56 |
| **Total** | **2,993** |

### Findings by component

| Component | Findings |
|---|---:|
| Debian 13.7 packages | 2,935 |
| Node.js dependencies | 44 |
| Python dependencies | 14 |
| Rust binaries (uv and uvx) | 0 |

These are package-level vulnerability findings. They should not
automatically be interpreted as unique CVEs or confirmed exploitable
runtime vulnerabilities.

## 4. Critical Vulnerability Analysis

The scan reported 12 Critical package-level findings associated
with four distinct CVE identifiers.

| CVE | Affected packages | Reported issue |
|---|---|---|
| CVE-2026-44172 | libmariadb-dev, libmariadb3, mariadb-client, mariadb-client-core, mariadb-common | SQL injection involving Big5 character-set handling |
| CVE-2026-49261 | libmariadb-dev, libmariadb3, mariadb-client, mariadb-client-core, mariadb-common | Arbitrary code execution involving wsrep_notify_cmd |
| CVE-2026-6653 | libxml2 | Denial of service involving crafted XML input |
| CVE-2026-60002 | openssh-client | Use-after-free during host-key re-exchange |

Trivy reported no fixed package version for these findings in
the captured scan report.

## 5. Installed Package Verification

The following packages were verified as installed inside the image:

| Package | Installed version |
|---|---|
| libmariadb-dev | 1:11.8.6-0+deb13u1 |
| libmariadb3 | 1:11.8.6-0+deb13u1 |
| mariadb-client | 1:11.8.6-0+deb13u1 |
| mariadb-client-core | 1:11.8.6-0+deb13u1 |
| mariadb-common | 1:11.8.6-0+deb13u1 |
| libxml2 | 2.12.7+dfsg+really2.9.14-2.1+deb13u3 |
| openssh-client | 1:10.0p1-7+deb13u4 |

## 6. Docker Image Investigation

Docker image history showed that the image installs packages
including mariadb-client, libmariadb-dev and ssh-client through
an apt-get installation layer.

The image also includes Python, Node.js, Chromium and various
development utilities.

This suggests an opportunity to review build-time and runtime
dependencies and reduce the image attack surface where compatible.

## 7. Secret Scan Results

The generated Trivy JSON report contained:

- Secret findings: 0 across the reported targets.
- Misconfiguration records: 0 in the JSON output.

This means no secrets were reported by the captured scan.
It does not guarantee that no secrets exist anywhere in the image.

A dedicated misconfiguration scan was not established by this
assessment.

## 8. Recommended Remediation

1. Review MariaDB package updates and vendor security advisories.
2. Evaluate a compatible security update for libxml2.
3. Update or remove openssh-client if it is not required.
4. Review Node.js and Python dependency findings.
5. Separate build-time dependencies from runtime dependencies
   where the image architecture permits.
6. Rebuild and rescan after approved changes.
7. Integrate image vulnerability scanning into CI/CD.

No package upgrades or application source modifications were
performed as part of this assessment.

## 9. Evidence Files

- frappe-bench-trivy.json: Complete Trivy JSON report.
- trivy-version.txt: Scanner and database version information.
- image-inspect.json: Docker image metadata.
- image-history.txt: Docker image build history.

## 10. Conclusion

The Trivy assessment identified 2,993 vulnerability findings,
including 12 Critical and 750 High findings.

The Critical findings were investigated by examining their
associated CVE identifiers, verifying installed packages and
reviewing Docker image history.

The results provide a baseline for security remediation.
The image should not be considered free of vulnerabilities until
approved fixes are applied, compatibility is tested and a
subsequent scan verifies the results.

The original application source code and scanned image were
left unchanged during this assessment.
