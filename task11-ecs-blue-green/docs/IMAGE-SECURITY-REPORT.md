
# Frappe CRM – Docker Image Security Report

## 1. Objective

Improve the security posture of the Frappe CRM Docker image before deploying it to AWS ECS Fargate.

The remediation focused on:
- Updating vulnerable Chromium packages.
- Removing unnecessary Vim packages.
- Scanning images using Amazon ECR Basic Scanning.
- Verifying the application runtime after remediation.

## 2. Image Information

| Image Tag | Purpose |
|---|---|
| `15` | Original Frappe CRM image |
| `15-patched-1` | Chromium security updates applied |
| `15-hardened-1` | Chromium updates and Vim removal |

**ECR Repository:**

`422346527555.dkr.ecr.ap-south-1.amazonaws.com/frappe-crm`

**AWS Region:** ap-south-1 (Mumbai)

## 3. Vulnerability Scan Comparison

Amazon ECR Basic Scanning results:

| Severity | Original (15) | Patched | Hardened |
|---|---:|---:|---:|
| Critical | 35 | 0 | 0 |
| High | 186 | 37 | 18 |
| Medium | 69 | 46 | 31 |
| Low | 16 | 7 | 7 |
| **Total** | **306** | **90** | **56** |

### Results

- Critical findings reduced from 35 to zero.
- Total findings reduced from 306 to 56.
- Overall reduction: approximately 81.7%.
- High-severity findings reduced from 186 to 18.

## 4. Security Remediation

### 4.1 Chromium Updates

The original image contained vulnerable Chromium packages.

Updated packages:

| Package | Original Version | Updated Version |
|---|---|---|
| chromium-common | 156.0.8078.79-1~deb12u1 | 156.0.8078.108-1~deb12u1 |
| chromium-headless-shell | 156.0.8078.79-1~deb12u1 | 156.0.8078.108-1~deb12u1 |

The updates were installed using Debian APT repositories.

### 4.2 Removal of Unnecessary Packages

Vim was identified as unnecessary for the application runtime.

The following remediation commands were used:

```bash
apt-get purge -y vim
apt-get autoremove --purge -y
```

Vim-related packages were removed without affecting the Bench CLI version.

### 4.3 Dockerfile

The hardened image was created using:

```dockerfile
FROM frappe-crm:15

USER root

RUN apt-get update \
    && apt-get install -y --only-upgrade chromium-common chromium-headless-shell \
    && apt-get purge -y vim \
    && apt-get autoremove --purge -y \
    && rm -rf /var/lib/apt/lists/*

USER frappe
```

The image retains the non-root `frappe` runtime user.

## 5. Application Verification

The following checks were completed against the hardened image:

| Verification | Result |
|---|---|
| Chromium package versions | Passed |
| Vim removal | Passed |
| Bench CLI version | 5.31.1 |
| Gunicorn version | 23.0.0 |
| Frappe Python source compilation | Passed |
| Frappe application code present | Passed |
| CRM application code present | Passed |
| Gunicorn startup | Passed |
| Gunicorn worker startup | Passed |
| Clean shutdown using Ctrl+C | Passed |

### Gunicorn Configuration

- Bind address: `0.0.0.0:8000`
- Workers: 2
- Threads: 4
- Worker class: gthread
- Application: `frappe.app:application`

**Important:** Full CRM functionality has not yet been verified with MariaDB, Redis, and a configured Frappe site.

## 6. Final ECR Scan Results

Hardened image:

`15-hardened-1`

Image index digest:

`sha256:63bf8465d97e0533b4517e635a8f0b7cdc512f9320baf21a72cbfe691d82f66c`

Linux AMD64 manifest digest:

`sha256:b32b65333e65396a5b2aa0d161715045748fc61f557db9b5f863485eb173a6d7`

Final scan status: COMPLETE

| Severity | Findings |
|---|---:|
| Critical | 0 |
| High | 18 |
| Medium | 31 |
| Low | 7 |
| **Total** | **56** |

## 7. Conclusion

The hardened Frappe CRM image achieved a significant reduction in reported vulnerabilities.

Critical vulnerabilities were reduced to zero, and total findings decreased by approximately 81.7% compared with the original image.

The hardened image is a candidate for the next deployment stage, subject to full application integration testing with the required database, Redis, and site configuration.

## 8. Next Steps

1. Complete Frappe CRM integration testing.
2. Provision AWS networking and ECS Fargate infrastructure using Terraform.
3. Configure Application Load Balancer and Blue-Green deployment.
4. Configure CloudWatch logging and health checks.
5. Implement GitHub Actions deployment and rollback workflows.
