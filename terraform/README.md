# AWS Infrastructure as Code with Terraform

This directory contains production-ready **Terraform** configuration files to define and manage core AWS infrastructure components. The setup is designed following Infrastructure-as-Code (IaC) best practices, strong security controls, and clean modularity.

---

## 1. Selected AWS Resources & Architecture Overview

The configuration defines **4 core AWS services/resources** forming a resilient web/application tier:

```
                      ┌────────────────────────────────────────────────────────┐
                      │                   AWS Cloud (us-east-1)                │
                      │                                                        │
                      │   ┌────────────────────────────────────────────────┐   │
                      │   │              Custom VPC (10.0.0.0/16)          │   │
                      │   │                                                │   │
                      │   │   ┌────────────────────────────────────────┐   │   │
                      │   │   │       Public Subnet (10.0.1.0/24)      │   │   │
                      │   │   │                                        │   │   │
                      │   │   │   ┌────────────────────────────────┐   │   │   │
Internet <───> IGW <──┼───┼───┼───┤ EC2 Instance (t3.micro)        │   │   │   │
                      │   │   │   │ - Ubuntu 24.04 LTS (Canonical) │   │   │   │
                      │   │   │   │ - IMDSv2 Enforced              │   │   │   │
                      │   │   │   │ - Encrypted EBS Volume (gp3)   │   │   │   │
                      │   │   │   │ - Security Group Protected     │   │   │   │
                      │   │   │   └────────────────────────────────┘   │   │   │
                      │   │   │                   │                    │   │   │
                      │   │   └───────────────────┼────────────────────┘   │   │
                      │   │                       │                    │   │   │
                      │   └───────────────────────┼────────────────────┘   │   │
                      │                           ▼                        │   │
                      │               ┌───────────────────────┐            │   │
                      │               │ S3 Application Bucket │            │   │
                      │               │ - SSE-S3 AES-256      │            │   │
                      │               │ - Bucket Versioning   │            │   │
                      │               │ - Public Access Block │            │   │
                      │               └───────────────────────┘            │   │
                      └────────────────────────────────────────────────────────┘
```

### Breakdown of Services:

1. **Amazon Virtual Private Cloud (VPC) & Networking** (`aws_vpc`, `aws_subnet`, `aws_internet_gateway`, `aws_route_table`, `aws_route_table_association`):
   - Custom CIDR block (`10.0.0.0/16`) with DNS support and DNS hostnames enabled.
   - Dedicated public subnet (`10.0.1.0/24`) in an availability zone with public IP auto-assignment.
   - Internet Gateway and default route table association (`0.0.0.0/0 -> IGW`) enabling network traffic.

2. **AWS Security Group (Firewall)** (`aws_security_group`):
   - Statefully controls inbound and outbound traffic at the hypervisor level.
   - Restricts HTTP (port 80) and HTTPS (port 443) for web ingress.
   - Restricts SSH (port 22) to authorized admin CIDR blocks.
   - Allows all outbound egress (`0.0.0.0/0`) for system updates, package downloads, and outbound API calls.

3. **Amazon Elastic Compute Cloud (EC2)** (`aws_instance`):
   - Dynamic data source lookup for the latest official Canonical Ubuntu 24.04 LTS Noble AMI.
   - Associated with the custom public subnet and security group.
   - **IMDSv2 Enforced**: Configured `http_tokens = "required"` to guard against Server-Side Request Forgery (SSRF) credential exposure.
   - **Encrypted Root Volume**: EBS root disk (`gp3`, 20 GiB) with encryption enabled at rest.

4. **Amazon Simple Storage Service (S3)** (`aws_s3_bucket` and sub-resources):
   - Cloud object storage for static assets, application backups, and persistent uploads.
   - **Unique Naming**: Utilizes `bucket_prefix` to ensure global namespace compliance without hardcoding static names.
   - **Versioning** (`aws_s3_bucket_versioning`): Retains historical versions to safeguard against accidental overwrites or deletes.
   - **Default Encryption** (`aws_s3_bucket_server_side_encryption_configuration`): Enforces SSE-S3 (AES256) server-side encryption at rest.
   - **Public Access Block** (`aws_s3_bucket_public_access_block`): Enforces all four S3 Block Public Access controls (`block_public_acls`, `block_public_policy`, `ignore_public_acls`, `restrict_public_buckets`).

---

## 2. Directory & File Structure

```text
terraform/
├── provider.tf             # Terraform & AWS provider requirements and default tags
├── variables.tf            # Input variable declarations with types, descriptions, and defaults
├── main.tf                 # Core AWS resource definitions (VPC, SG, EC2, S3)
├── outputs.tf              # Resource outputs (IDs, public/private IPs, bucket ARN)
├── terraform.tfvars.example# Sample variable values for environment customization
└── README.md               # Architecture documentation and usage guide
```

---

## 3. Security & Compliance Highlights

- **Zero Hardcoded Credentials**: No AWS access keys, secret keys, or passwords are baked into any file. Terraform leverages standard AWS SDK credential resolution (environment variables, `~/.aws/credentials`, or IAM roles/SSO).
- **Least-Privilege Networking**: Ingress traffic is strictly scoped by port; SSH is parameter-controlled rather than permanently open.
- **Data Protection at Rest**: Both the EC2 root block device and the S3 storage bucket utilize AES-256 encryption.
- **Instance Metadata Protection**: IMDSv2 is strictly enforced (`http_tokens = "required"`, `http_put_response_hop_limit = 1`), completely mitigating legacy IMDSv1 SSRF attack vectors.
- **Default Resource Tagging**: Standardized tagging (`Project`, `Environment`, `ManagedBy = "Terraform"`) propagates automatically across all provisioned resources via provider default tags.

---

## 4. Usage & Validation Instructions

> [!IMPORTANT]
> **Strict Guidelines Adhered to:**
> - **DO NOT run `terraform apply` or `terraform destroy`**
> - **DO NOT provision any actual AWS cloud resources**

### Step 1: Format Check
Verify all files comply with standard HashiCorp HCL style conventions:
```bash
terraform fmt -check
```
To auto-format files if modified:
```bash
terraform fmt
```

### Step 2: Initialize Provider Plugins
Initialize the local working directory and download the AWS provider schema:
```bash
terraform init -backend=false
```

### Step 3: Validate Syntax and Internal References
Validate configuration syntax, attribute types, and resource reference links:
```bash
terraform validate
```
Expected output:
```text
Success! The configuration is valid.
```

### Step 4: Preview Plan (Dry-Run Only)
If credentials exist in your local shell environment and you wish to preview resource diffs **without** provisioning:
```bash
terraform plan
```
*(Remember: Do NOT execute `terraform apply`)*
