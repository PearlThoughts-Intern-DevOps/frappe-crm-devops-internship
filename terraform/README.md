# Frappe CRM - AWS ECS Fargate Blue-Green Terraform Infrastructure

This directory contains production-ready Terraform modules to provision the complete AWS infrastructure for **Frappe CRM** on **AWS ECS Fargate** with a zero-downtime **Blue-Green Deployment** strategy.

---

## Infrastructure Components

| Component | AWS Service | Specification / Role |
| :--- | :--- | :--- |
| **Networking** | Amazon VPC | Multi-AZ (2 Public Subnets, 2 Private Subnets, IGW, NAT Gateway) |
| **Load Balancing** | Application Load Balancer | Port 80 (Prod) & Port 8080 (Test), Blue & Green Target Groups |
| **Container Compute** | Amazon ECS Fargate | Task CPU: 1024 (1 vCPU), Task Memory: 2048 MB, awsvpc mode |
| **Deployment Engine**| AWS CodeDeploy | Strategy: `BLUE_GREEN`, Traffic Control: `WITH_TRAFFIC_CONTROL` |
| **Database** | Amazon RDS MariaDB | Version: 10.11, Storage: gp3, Parameter Group: utf8mb4 |
| **Cache & Queue** | Amazon ElastiCache | Redis 7.0 engine, private cluster |
| **Registry** | Amazon ECR | Private repository with scan-on-push & automated pruning policy |
| **Monitoring** | Amazon CloudWatch | Container Insights, Log Group `/ecs/frappe-crm`, Metric Alarms |
| **Auto-Rollback** | CodeDeploy + CloudWatch | Instant rollback on deployment error or 5XX / unhealthy thresholds |

---

## Quick Start

### 1. Initialize Terraform
```bash
terraform init
```

### 2. Review Execution Plan
```bash
terraform plan
```

### 3. Apply Infrastructure
```bash
terraform apply -auto-approve
```

---

## Outputs
- `alb_dns_name`: Public DNS hostname of the Application Load Balancer
- `production_url`: HTTP port 80 URL for end-user traffic
- `test_validation_url`: HTTP port 8080 URL for pre-traffic Blue-Green validation
- `ecr_repository_url`: ECR image repository URI
- `ecs_cluster_name`: Name of the ECS cluster (`frappe-crm-cluster`)
- `ecs_service_name`: Name of the ECS service (`frappe-crm-service`)
- `codedeploy_application_name`: CodeDeploy application name
- `codedeploy_deployment_group_name`: CodeDeploy deployment group name
