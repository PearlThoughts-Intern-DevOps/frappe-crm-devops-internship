# Terraform AWS Infrastructure

## Overview

This project defines four AWS resources using Terraform:

1. AWS VPC
2. AWS Subnet
3. AWS Security Group
4. AWS S3 Bucket

## Project Files

- provider.tf: AWS provider configuration
- main.tf: AWS resource definitions
- variables.tf: Input variables
- outputs.tf: Resource outputs
- terraform.tfvars.example: Example configuration
- .gitignore: Excluded files

## Prerequisites

- Terraform CLI
- Git

AWS credentials are not required to review the code.

## Important

This project is for configuration demonstration only.

No AWS resources have been provisioned.

Do not execute:

- terraform apply
- terraform destroy

## Validation

You may review the files or run:

```bash
terraform fmt -check
```

This checks formatting without provisioning resources.

## Security

No AWS credentials are hardcoded.
The S3 bucket is intended to be private.
The security group does not define inbound access.