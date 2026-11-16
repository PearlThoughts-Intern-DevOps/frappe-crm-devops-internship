# AWS Infrastructure Provisioning with Terraform

## Overview

This project demonstrates Infrastructure as Code (IaC) using **Terraform** to define AWS infrastructure.

It covers networking, compute, storage, container image management, and container orchestration using Amazon ECS with AWS Fargate.

The Terraform configuration is organized into separate files based on resource responsibilities to improve readability and maintainability.

**Important:** This project focuses on writing and validating Terraform configurations. No AWS infrastructure was provisioned as part of this assignment.

## Architecture

The project defines the following AWS resources:

### 1. Networking

- Amazon Virtual Private Cloud (VPC)
- Public Subnet
- Internet Gateway
- Public Route Table
- Route Table Association
- EC2 Security Group
- ECS Security Group

### 2. Compute

- Amazon EC2 instance
- Amazon Linux 2023 AMI retrieved dynamically using a Terraform data source

### 3. Storage

- Amazon S3 bucket
- S3 Public Access Block to prevent public access

### 4. Container Registry

- Amazon Elastic Container Registry (ECR)
- Immutable image tags
- Image scanning on push

### 5. Container Orchestration

- Amazon Elastic Container Service (ECS) Cluster
- ECS Task Definition
- ECS Service
- AWS Fargate launch type

AWS Fargate provides serverless container compute, so there is no need to manage EC2 instances for the ECS workload.

### 6. IAM

- ECS Task Execution IAM Role
- AWS-managed `AmazonECSTaskExecutionRolePolicy`

The execution role allows ECS tasks to perform required actions such as pulling container images from ECR.

## Architecture Flow

1. A Docker image is stored in Amazon ECR.
2. The ECS Task Definition specifies the container image, CPU, memory, networking mode, and container port.
3. The ECS Service maintains the desired number of running tasks.
4. AWS Fargate provides the compute capacity to run the containers.

## Technologies Used

- Terraform
- AWS
- Amazon VPC
- Amazon EC2
- Amazon S3
- Amazon ECR
- Amazon ECS
- AWS Fargate
- AWS IAM

## Project Structure

```text
terraform-aws-infrastructure/
│
├── versions.tf
├── provider.tf
├── variables.tf
├── networking.tf
├── compute.tf
├── storage.tf
├── containers.tf
├── iam.tf
├── task-definition.tf
├── ecs-service.tf
├── outputs.tf
├── .gitignore
└── README.md
```

## Terraform File Description

| File | Responsibility |
|---|---|
| `versions.tf` | Defines Terraform and AWS provider version requirements |
| `provider.tf` | Configures the AWS provider and region |
| `variables.tf` | Defines reusable input variables |
| `networking.tf` | Creates VPC, subnet, internet gateway, route table, and security groups |
| `compute.tf` | Defines the EC2 instance and dynamically retrieves the AMI |
| `storage.tf` | Creates the S3 bucket and public access block |
| `containers.tf` | Defines the ECR repository and ECS cluster |
| `iam.tf` | Creates the ECS task execution role and attaches its policy |
| `task-definition.tf` | Defines the Fargate task configuration |
| `ecs-service.tf` | Defines the ECS Fargate service |
| `outputs.tf` | Defines useful infrastructure outputs |

## Key Terraform Concepts Demonstrated

- Resource blocks and data sources
- Input variables and output values
- Resource references and implicit dependencies
- Terraform provider configuration
- Dynamic AMI selection using data sources
- JSON encoding using `jsonencode()`
- IAM roles and policy attachments
- ECS Task Definitions and Services
- Fargate networking using `awsvpc`
- Modular Terraform file organization

## Prerequisites

- Terraform CLI installed
- Visual Studio Code or another code editor
- AWS account and credentials for actual AWS deployment

AWS credentials are not hardcoded in the configuration. Standard AWS credential mechanisms can be used when interacting with an AWS account.

## Terraform Formatting and Validation

The following commands were used to format, initialize, and validate the Terraform configuration.

**1. Format Terraform files**

```bash
terraform fmt
```

**2. Initialize the Terraform working directory**

```bash
terraform init
```

**3. Validate the configuration**

```bash
terraform validate
```

Successful validation confirms that Terraform accepts the configuration's syntax and structure. It does not guarantee that every resource will deploy successfully.

## Important Notes

- No `terraform apply` or `terraform destroy` commands were executed.
- No AWS infrastructure was provisioned.
- The ECS Task Definition references an ECR image tagged `latest`. That image must exist in ECR before the task can successfully start.
- The ECS Service uses a public subnet with public IP assignment.
- The ECS Security Group allows inbound traffic on port `5000`. Review and restrict this rule before an actual deployment.
- CloudWatch log forwarding has not been configured in the ECS Task Definition.

## Conclusion

This project demonstrates how Terraform can define AWS infrastructure in a modular and maintainable way.

It provides practical exposure to AWS networking, compute, storage, IAM, container registries, and serverless container orchestration using Amazon ECS with Fargate.