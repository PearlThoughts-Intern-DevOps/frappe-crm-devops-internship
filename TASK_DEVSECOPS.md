# DevSecOps Security Scanning & Vulnerability Assessment Report
**Project:** Frappe CRM  
**Target Environment:** Local Docker Compose & Kubernetes Deployment  
**Auditor:** Bulbul Das  
**Date:** November 18, 2026  
**Status:** Complete  

---

## Executive Summary

As part of the **Frappe CRM DevSecOps Security Assessment**, a multi-layered security evaluation was performed across the entire application lifecycle. The assessment integrated static analysis, container image vulnerability scanning, dependency analysis (Software Composition Analysis), secret detection, and Infrastructure-as-Code (IaC) compliance checks.

The assessment utilized industry-standard open-source DevSecOps tools:
- **Trivy (v0.76.2)**: For container image vulnerability scanning and dependency file auditing.
- **Gitleaks (v8.30.1)**: For scanning git commit history and working tree for exposed credentials, API keys, and sensitive tokens.
- **Checkov (v3.4.5)**: For static code analysis of Kubernetes manifests and Docker configurations against CIS benchmarks and security best practices.

### Key Assessment Findings Summary

| Scan Category | Tool | Scope / Targets | Total Finding Instances | Unique CVEs / Violations | Critical | High | Medium | Low |
| :--- | :--- | :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| **Container Images** | Trivy | `bench`, `mariadb`, `redis` | **4,283** | **2,291 unique CVEs** | **10 unique** (18 pkgs) | **474 unique** (922 pkgs) | **1,209 unique** | **598 unique** |
| **Dependencies (SCA)** | Trivy | `yarn.lock`, `package.json`, `pyproject.toml` | **198** | **115 unique CVEs** | **4 unique** | **50 unique** | **44 unique** | **17 unique** |
| **Secret Detection** | Gitleaks | Git History (6,243 commits) & Filesystem | **6 leaks** | **3 distinct sources** | **3 Real**, **2 Templates**, **1 Upstream** | — | — | — |
| **IaC Configurations** | Checkov | Kubernetes Manifests & Docker Compose | **42 failed checks** | **15 distinct policies** | **0** | **18 checks** | **18 checks** | **6 checks** |
| **Total Security Findings** | | | **4,529 instances** | **2,424 unique issues** | **14 unique CVEs + 3 Secrets** | **524 unique CVEs/Checks** | **1,227** | **604** |

---

## 1. DevSecOps Fundamentals & The Importance of Security Scanning

### 1.1 What is DevSecOps?
DevSecOps represents the natural evolution of DevOps by embedding security practices, automation, and governance into every stage of the software development lifecycle (SDLC)—from planning and coding to build, test, deployment, and runtime monitoring. 

Rather than treating security as an external audit performed right before release, DevSecOps establishes a **shared responsibility model** where developers, operations engineers, and security specialists collaborate continuously.

```
       Plan  ───►  Code  ───►  Build  ───►  Test
        ▲                                    │
        │           DevSecOps Pipeline       ▼
     Monitor ◄──  Deploy  ◄───  Release  ◄── Secure
```

### 1.2 The Shift-Left Security Philosophy
- **Traditional Security (Shift-Right):** Vulnerability assessments and penetration testing were conducted on production or pre-production staging environments. Remediation at this stage is exponentially expensive, causes deployment delays, and risks breaking core business logic.
- **Shift-Left Security:** Moving security controls as close to developer commit and continuous integration (CI) as possible. Vulnerabilities, hardcoded secrets, and misconfigurations are caught at the developer workstation (via IDE plugins and pre-commit hooks) and pull-request build gates.
- **Cost of Remediation:** Industry studies (NIST, IBM Security) demonstrate that fixing a defect or security flaw during requirements/coding costs **10x to 100x less** than remediating an exploited vulnerability in production.

### 1.3 Core Pillars of Automated Scanning
1. **Static Application Security Testing (SAST) & Secret Scanning (Gitleaks):** Identifies plaintext secrets, passwords, encryption keys, and vulnerable source code patterns before they enter the repository.
2. **Software Composition Analysis (SCA) (Trivy fs / Audit):** Maps open-source dependencies (Python wheels, Node/NPM packages) against National Vulnerability Database (NVD) and GitHub Advisory Database (GHSA) CVE entries.
3. **Container Image Scanning (Trivy image):** Audits base operating system packages (glibc, openssl, libxml2) and installed runtime binaries inside Docker images.
4. **Infrastructure as Code (IaC) Scanning (Checkov):** Validates Kubernetes YAMLs, Docker Compose, Terraform, and Helm charts against hardening benchmarks (e.g., CIS Kubernetes Benchmark) to prevent privilege escalation and unconfined network exposure.

---

## 2. Container Image Vulnerability Analysis (Trivy)

The Frappe CRM stack runs three core container images defined in `docker/docker-compose.yml` and Kubernetes manifests:
1. `frappe/bench:latest` (Application runtime, bench CLI, Python 3.11/12, Node.js, Redis clients)
2. `mariadb:10.8` (Relational database management system)
3. `redis:alpine` (In-memory caching and WebSocket pub/sub broker)

### 2.1 Scan Results Overview

```
frappe/bench:latest   │ 13 CRITICAL │ 839 HIGH │ 1457 MEDIUM │ 1313 LOW
mariadb:10.8          │  5 CRITICAL │  83 HIGH │  409 MEDIUM │  163 LOW
redis:alpine          │  0 CRITICAL │   0 HIGH │    1 MEDIUM │    0 LOW
```

### 2.2 In-Depth Analysis: `frappe/bench:latest`
- **Base OS:** Debian GNU/Linux 13.7 (trixie/sid)
- **Total Packages Scanned:** 411 OS packages + Python packages + Node packages + Rust binaries.
- **Total Vulnerabilities:** 3,622

#### Highlighted Critical & High Vulnerabilities:
1. **CVE-2026-44172 (libmariadb-dev & libmariadb3 - CRITICAL):**
   - **Vulnerability:** MariaDB client library improperly handles the Big5 character set in `mysql_real_escape_string()`, allowing attackers to bypass SQL injection sanitization filters by injecting multi-byte sequence characters.
   - **Impact:** SQL Injection leading to arbitrary data leakage, authentication bypass, or data modification in CRM databases.
   - **Remediation:** Update `libmariadb3` to the patched distribution release or configure UTF-8 exclusively across all database client handshakes.
2. **CVE-2026-49261 (libmariadb-dev & libmariadb3 - CRITICAL):**
   - **Vulnerability:** Arbitrary command execution vulnerability via `wsrep_notify_cmd` parameter parsing.
   - **Impact:** Remote code execution inside the container if the database client or node accepts untrusted replication control parameters.
3. **CVE-2026-6653 (libxml2 - CRITICAL):**
   - **Vulnerability:** Use-after-free defect in libxml2 XML parser during entity expansion.
   - **Impact:** Denial of Service (DoS) and potential memory corruption via maliciously crafted XML documents uploaded or ingested by CRM contact/email parsers.

### 2.3 In-Depth Analysis: `mariadb:10.8`
- **Base OS:** Ubuntu 22.04 LTS (Jammy)
- **Total Vulnerabilities:** 660 (5 Critical, 83 High)
- **Root Cause:** The `mariadb:10.8` image contains a bundled `mysqld-exporter` or helper binary compiled with an outdated Go runtime (`stdlib v1.16.7`).

#### Highlighted Critical Go Runtime Flaws:
1. **CVE-2025-68121 (CRITICAL):** Incorrect certificate validation during TLS session resumption in `crypto/tls`.
2. **CVE-2023-24538 & CVE-2023-24540 (CRITICAL):** HTML template injection and backtick sanitization bypass in `html/template`.
3. **CVE-2022-23806 (CRITICAL):** Elliptic curve validation defect in `crypto/elliptic` where `IsOnCurve` returns true for invalid field points.
4. **Remediation:** MariaDB 10.8 is end-of-life (EOL). Migrate to **MariaDB 10.11 LTS** or **MariaDB 11.4 LTS** which use updated base operating systems and contemporary Go toolchains.

### 2.4 In-Depth Analysis: `redis:alpine`
- **Base OS:** Alpine Linux 3.23.8
- **Total Vulnerabilities:** 1 (0 Critical, 0 High, 1 Medium)
- **Assessment:** Excellent security profile. The minimal surface of Alpine Linux (musl libc, BusyBox) demonstrates the security benefits of using micro-containers.

---

## 3. Dependency Vulnerability Analysis (SCA)

The application dependencies were scanned using Trivy's filesystem analyzer across Python (`pyproject.toml`) and Node.js (`package.json`, `yarn.lock`, `frappe-ui/package.json`).

### 3.1 Severity Distribution
- **Total Dependencies Findings:** 198
- **Critical:** 4
- **High:** 90
- **Medium:** 77
- **Low:** 27

### 3.2 Critical Vulnerabilities Breakdown

| Advisory / CVE | Package | Installed | Fixed Version | Severity | Attack Vector & Impact |
| :--- | :--- | :---: | :---: | :---: | :--- |
| **GHSA-cg2g-xh64-v4q7** | `dompurify` | `3.4.5` | `3.4.17` | **CRITICAL** | **Template Injection Bypass:** In DOM output mode, split template expressions survive inside attached shadow root nodes, allowing Stored XSS in Frappe UI CRM views. |
| **CVE-2026-104848** | `tinypool` | `1.1.1` | `2.1.1` | **CRITICAL** | **Prototype Pollution to RCE:** Worker pool options parameter allows Prototype Pollution leading to arbitrary code execution during background task spawning. |
| **CVE-2026-104849** | `tinypool` | `1.1.1` | `2.1.2` | **CRITICAL** | **Prototype Pollution Gadget:** Prototype pollution gadget in `tinypool.run()` options can be chained to gain remote execution. |

### 3.3 Significant High-Severity Findings
- **GHSA-j95f-988m-3j2f (`@tiptap/core` 3.26.0 -> 3.30.5):** Quadratic Regular Expression Denial of Service (ReDoS) in block and inline Markdown parsing. An attacker sending a crafted notes or message body can freeze the CRM UI.
- **GHSA-g2v6-rqmx-r4w6 (`@vue/server-renderer` 3.5.27 -> 3.5.42):** Cross-site Scripting (XSS) via missing carriage-return (`\r`) parsing in attribute-name blacklist during Server-Side Rendering (SSR).
- **CVE-2026-102276 (`brace-expansion` 1.1.14 -> 1.1.19 / 2.1.5):** Denial of Service via stack exhaustion from deeply nested brace patterns.

---

## 4. Secret & Credential Exposure Analysis (Gitleaks)

Gitleaks performed high-entropy token analysis and regex-based pattern matching across **6,243 Git commits** (116.6 MB repository history).

### 4.1 Identified Secret Exposures

```
Total Secrets Detected: 6
Rule Triggered: generic-api-key
Status: EXPOSED IN GIT HISTORY & UNTRACKED LOCAL CONFIGS
```

| # | File Path | Line | Rule ID | Exposed Secret (Masked) | Commit / Source |
| :-: | :--- | :-: | :--- | :--- | :--- |
| 1 | `kubernetes/02-secret.yaml.example` | 31 | `generic-api-key` | `MARIADB_ROOT_PASSWORD: [REDACTED_TEMPLATE_VALUE]` | Commit `38de6c7c` |
| 2 | `kubernetes/02-secret.yaml.example` | 35 | `generic-api-key` | `FRAPPE_ADMIN_PASSWORD: [REDACTED_TEMPLATE_VALUE]` | Commit `38de6c7c` |
| 3 | `backups/20261104_160131_crm_localhost/...json` | 3 | `generic-api-key` | `"db_password": "[REDACTED_DATABASE_PASSWORD]"` | Commit `e02d920a` |
| 4 | `backups/20261104_173848_crm_localhost/...json` | 3 | `generic-api-key` | `"db_password": "[REDACTED_DATABASE_PASSWORD]"` | Commit `e02d920a` |
| 5 | `backups/20261105_101320_crm_localhost/...json` | 3 | `generic-api-key` | `"db_password": "[REDACTED_DATABASE_PASSWORD]"` | Commit `e02d920a` |
| 6 | `crm/twilio/api.py` | 96 | `generic-api-key` | `auth_token = '[REDACTED_TWILIO_AUTH_TOKEN]'` | Upstream Frappe (`b3abc00e`) |
| 7 | `kubernetes/02-secret.yaml` *(untracked)* | 11, 13 | `k8s-secret` | Base64 dummy values (e.g. default '123' and 'admin') | Working tree |

### 4.2 Security Risk Evaluation
- **Committed Database Backups:** Site config backup files contain active database passwords in cleartext. Anyone with clone access to the Git repository can extract production database credentials.
- **Base64 is NOT Encryption:** Base64 encoding in Kubernetes `Secret` definitions (`02-secret.yaml`) is reversible encoding, not encryption.
- **Upstream Hardcoded API Keys:** The Twilio authentication token in `crm/twilio/api.py` is hardcoded directly in Python code rather than retrieved from environment variables or Frappe site settings.

---

## 5. Infrastructure as Code (IaC) Compliance Audit (Checkov)

Static security analysis of the Kubernetes manifests (`kubernetes/*.yaml`) and Docker configurations was conducted using Checkov against CIS Kubernetes Benchmark standards.

### 5.1 Checkov Execution Summary
- **Passed Checks:** 227
- **Failed Checks:** 42
- **Skipped Checks:** 0
- **Total Evaluated Assertions:** 269

### 5.2 Top Failed Security Policies & Risks

| Policy ID | Check Description | Affected Resources | Security Risk |
| :--- | :--- | :--- | :--- |
| **CKV_K8S_23** | Minimize the admission of root containers | `Deployment/frappe`, `StatefulSet/mariadb`, `Deployment/redis` | If a container is compromised, the attacker has host root privileges inside the container namespace. |
| **CKV_K8S_20** | Containers should not run with `allowPrivilegeEscalation` | `Deployment/frappe`, `StatefulSet/mariadb`, `Deployment/redis` | Allows child processes to gain more privileges than the parent process (e.g., via SUID binaries). |
| **CKV_K8S_22** | Use read-only filesystem for containers | `Deployment/frappe`, `StatefulSet/mariadb`, `Deployment/redis` | Allows attackers to download and execute rootkits, backdoors, or cryptominers directly into ephemeral disk. |
| **CKV_K8S_37** | Minimize admission of containers with capabilities | `Deployment/frappe`, `StatefulSet/mariadb`, `Deployment/redis` | Containers run with default Linux capabilities instead of dropping `ALL` capabilities and adding only necessary ones. |
| **CKV_K8S_31** | Ensure seccomp profile is set to `runtime/default` | `Deployment/frappe`, `StatefulSet/mariadb`, `Deployment/redis` | Unrestricted system call table available to container processes. |
| **CKV_K8S_38** | Mount ServiceAccount tokens only where necessary | `Deployment/frappe`, `StatefulSet/mariadb`, `Deployment/redis` | Default Kubernetes API tokens are automatically mounted inside pods, enabling cluster reconnaissance. |
| **CKV_K8S_35** | Prefer secrets as files over environment variables | `Deployment/frappe`, `StatefulSet/mariadb` | Sensitive passwords exposed in process lists (`/proc/$PID/environ`), container inspection (`docker inspect`), and log crash dumps. |
| **CKV_K8S_14** | Image tag should be fixed (not `:latest`) | `Deployment/frappe`, `redis`, `mariadb` | Non-deterministic builds, inability to roll back safely, and risk of breaking changes upon image re-pull. |
| **CKV_K8S_43** | Image should use immutable digest (`sha256`) | `Deployment/frappe`, `redis`, `mariadb` | Image tags can be modified or spoofed upstream; digests guarantee cryptographic integrity. |

---

## 6. Comprehensive Severity Matrix & Risk Categorization

The identified security findings are categorized based on **Common Vulnerability Scoring System (CVSS v3.1)** ratings and operational exploitability:

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    FRAUGHT SECURITY EXPOSURE PYRAMID                        │
├─────────────────────────────────────────────────────────────────────────────┤
│  CRITICAL (28 findings): Remote Code Execution, Leaked Plaintext Secrets,   │
│                          SQL Injection, Prototype Pollution                 │
│                                                                             │
│  HIGH (1,030 findings):  Host privilege escalation vectors, Cross-Site     │
│                          Scripting (XSS), Quadratic ReDoS, Root containers  │
│                                                                             │
│  MEDIUM (1,962 findings): Denial of Service, unpinned digests, plaintext    │
│                          environment variable credentials, weak ciphers     │
│                                                                             │
│  LOW (1,509 findings):   Missing seccomp annotations, informative leaks,    │
│                          minor memory leaks in non-exposed utilities        │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Risk Prioritization Matrix

```
       ▲ High ┌───────────────────────┬───────────────────────┐
       │      │      PRIORITY 2       │      PRIORITY 1       │
       │      │  High Vulnerabilities │  Critical CVEs        │
       │      │  Root Pod Execution   │  Exposed DB Passwords │
IMPACT │      │  Missing Drop Caps    │  Twilio Token Leak    │
       │      ├───────────────────────┼───────────────────────┤
       │      │      PRIORITY 4       │      PRIORITY 3       │
       │      │  Low Severity Checks  │  Medium CVSS Issues   │
       │      │  Minor Info Leaks     │  Missing Resource Lim │
       │ Low  │  Unpinned minor pkgs  │  Env Var Secrets      │
       └──────┴───────────────────────┴───────────────────────┘
              Low ───────────────────► High
                       EXPLOITABILITY
```

---

## 7. Actionable Solutions & Remediation Plan

To address the findings without modifying upstream business logic or breaking environment compatibility, the following remediation roadmap is recommended:

### 7.1 Secret Sanitization & Prevention
1. **Remove Committed Backups from Git Tracking:**
   ```bash
   git rm -r --cached backups/
   echo "backups/" >> .gitignore
   echo "kubernetes/02-secret.yaml" >> .gitignore
   echo "*.backup.json" >> .gitignore
   ```
2. **Purge Secrets from History:**
   Use `git-filter-repo` to permanently erase sensitive site configurations and credentials from the Git tree.
3. **Pre-Commit Git Hooks:**
   Enforce Gitleaks on local developer machines before any commit can be created:
   ```yaml
   # .pre-commit-config.yaml
   - repo: https://github.com/gitleaks/gitleaks
     rev: v8.30.1
     hooks:
       - id: gitleaks
   ```
4. **Secrets Management:**
   Migrate from Kubernetes plaintext secrets to **HashiCorp Vault**, **AWS Secrets Manager**, or **Sealed Secrets**. Mount secrets as ephemeral files in `/etc/secrets` rather than environment variables (`CKV_K8S_35`).

---

### 7.2 Container Image Hardening
1. **Pin Specific Image Digests:**
   Never use `latest` in production. Pin specific immutable SHA256 digests:
   ```yaml
   image: frappe/bench:v15.0.0@sha256:5f0a07a69768...
   image: mariadb:10.11.8-jammy@sha256:...
   image: redis:7.2.4-alpine3.19@sha256:...
   ```
2. **Upgrade MariaDB to Supported LTS:**
   Replace the deprecated MariaDB 10.8 with MariaDB 10.11 LTS or 11.4 LTS to eliminate the 5 Critical Go runtime CVEs.
3. **Minimize Container Attack Surface:**
   Adopt multi-stage Docker builds and non-root distroless runtime containers.

---

### 7.3 Dependency Hardening (SCA Remediation)
1. **Frontend / Node.js Packages:**
   - Upgrade `dompurify` from `3.4.5` to `^3.4.17` (Resolves Critical DOM injection `GHSA-cg2g-xh64-v4q7`).
   - Upgrade `tinypool` from `1.1.1` to `^2.1.2` (Resolves Critical RCE `CVE-2026-104848`).
   - Upgrade `@tiptap/core` to `^3.30.5` (Resolves High ReDoS `GHSA-j95f-988m-3j2f`).
   - Execute regression tests to ensure frontend components render without breaking changes.
2. **Python Dependencies:**
   - Remove hardcoded credentials in `crm/twilio/api.py` and replace with `frappe.conf.get("TWILIO_AUTH_TOKEN")`.
   - Update `requests` to `>=2.32.0` in `pyproject.toml`.

---

### 7.4 Hardened Kubernetes Manifest Template

To resolve the 42 Checkov failed checks, apply the following hardened `securityContext` and pod specification:

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: frappe-crm-bench
  namespace: frappe-crm
spec:
  replicas: 1
  template:
    metadata:
      labels:
        app: frappe-crm-bench
    spec:
      # CKV_K8S_38: Disable automatic ServiceAccount token mounting
      automountServiceAccountToken: false
      
      # Pod-level security context
      securityContext:
        runAsNonRoot: true
        runAsUser: 1000
        runAsGroup: 1000
        fsGroup: 1000
        seccompProfile:
          type: RuntimeDefault  # CKV_K8S_31

      containers:
        - name: frappe-bench
          # CKV_K8S_14 & CKV_K8S_43: Pinned version with digest
          image: frappe/bench:v15.0.0@sha256:5f0a07a69768b4ef84c7bb2cf8dbb3...
          imagePullPolicy: Always # CKV_K8S_15
          
          # Container-level security context
          securityContext:
            allowPrivilegeEscalation: false # CKV_K8S_20
            readOnlyRootFilesystem: true     # CKV_K8S_22
            capabilities:
              drop:
                - ALL                        # CKV_K8S_37, CKV_K8S_28
          
          # CKV_K8S_10, 11, 12, 13: CPU & Memory Requests and Limits
          resources:
            requests:
              cpu: "250m"
              memory: "512Mi"
            limits:
              cpu: "1000m"
              memory: "2Gi"

          # CKV_K8S_35: Mount secrets from volume rather than env vars
          volumeMounts:
            - name: secrets-volume
              mountPath: /etc/secrets
              readOnly: true
            - name: tmp-volume
              mountPath: /tmp

      volumes:
        - name: secrets-volume
          secret:
            secretName: frappe-crm-secrets
        - name: tmp-volume
          emptyDir: {}
```

---

### 7.5 CI/CD DevSecOps Implementation

Automate continuous security checks via the included GitHub Actions workflow (`.github/workflows/devsecops-pipeline.yml`):
- **PR Gating:** Reject pull requests introducing new High or Critical vulnerabilities.
- **Secret Blocking:** Gitleaks runs as an immediate blocking check before any build starts.
- **Compliance Artifacts:** Scan reports in JSON and SARIF format are uploaded to GitHub Security tab for centralized visibility.

---

## 8. Conclusion

This DevSecOps assessment establishes a transparent baseline of Frappe CRM's security posture. By shifting security left, addressing exposed credentials, upgrading vulnerable frontend packages (`dompurify`, `tinypool`), and hardening Kubernetes pod specifications, Frappe CRM can achieve high operational resilience and adhere to enterprise cloud security benchmarks.
