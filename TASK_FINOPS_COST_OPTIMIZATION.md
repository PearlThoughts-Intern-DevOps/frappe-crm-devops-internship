# AWS Cost Optimization (FinOps) — Frappe CRM on ECS Fargate

**Project:** Frappe CRM Deployment (`ap-southeast-2` | AWS Project `865188471560`)  
**Branch / PR:** `task-bulbul-das` → PR `#88` (`main`)

---

## Overview

This document summarizes the **FinOps (cost-optimization)** practices implemented in Terraform (`terraform/`) and CodeDeploy (`docker/`) to avoid idle spend while keeping the application reliable during business/demo hours.

---

## FinOps Controls Implemented

| Practice | What Was Configured | Why It Saves Money | Where |
|---|---|---|---|
| **1. Cost Tags** | Auto-tags every resource (`Project`, `Environment`, `ManagedBy`, `DeploymentStrategy`, `Application`) | Tracks spend per project/app in AWS Billing | [provider.tf](terraform/provider.tf) |
| **2. ECS Auto Scaling** | Scales between **1–4 tasks** targeting **70% CPU** / **75% Memory** (`60s` out / `300s` in cooldown) | Runs only the containers needed for current load | [autoscaling.tf](terraform/autoscaling.tf) |
| **3. Off-Hours Schedule** | Scales down at night & weekends in `Asia/Kolkata` timezone *(see schedule below)* | Cuts overnight & weekend Fargate compute by **50%** | [autoscaling.tf](terraform/autoscaling.tf) |
| **4. Fargate Spot** | Attaches `FARGATE` + `FARGATE_SPOT` to cluster; `appspec.yaml` sets `1` On-Demand base + Spot (`Weight: 3`) | Uses discounted Spot capacity for secondary/burst tasks *(see note below)* | [ecs.tf](terraform/ecs.tf), [appspec.yaml](docker/appspec.yaml) |
| **5. Free S3 Endpoint** | Gateway VPC Endpoint (`com.amazonaws.ap-southeast-2.s3`) on private route table | Routes ECR image pulls directly over S3 instead of paying NAT per-GB fees | [vpc.tf](terraform/vpc.tf) |
| **6. Single NAT Gateway** | 1 NAT Gateway instead of 1 per Availability Zone | Avoids paying duplicate hourly NAT Gateway charges | [vpc.tf](terraform/vpc.tf) |
| **7. Graviton DB & Cache** | RDS MariaDB `db.t4g.micro` (`gp3` `20–50 GB` autoscale) + single-node Redis `cache.t4g.micro` | Right-sized ARM instances; disk grows only when needed | [rds.tf](terraform/rds.tf), [redis.tf](terraform/redis.tf) |
| **8. ECR & Log Cleanup** | ECR deletes untagged images after **7 days** & keeps last **15** tagged; CloudWatch logs expire after **14 days** | Stops old images and logs from accumulating storage bills | [ecr.tf](terraform/ecr.tf), [cloudwatch.tf](terraform/cloudwatch.tf) |
| **9. Clean Cutover & CI** | CodeDeploy terminates old Blue tasks **5 mins** after success; PR CI runs validation only (no auto-deploy) | Prevents duplicate running tasks and unnecessary build minutes | [codedeploy.tf](terraform/codedeploy.tf), [deploy-ecs-bluegreen.yml](.github/workflows/deploy-ecs-bluegreen.yml) |

---

## Off-Hours Scaling Schedule (`Asia/Kolkata`)

| Window | Cron | Tasks (`Min → Max`) | Goal |
|---|---|---|---|
| **Mon–Fri 9:00 AM** | `cron(0 9 ? * MON-FRI *)` | `2 → 4` | Full 2-AZ High Availability for work & demo hours |
| **Mon–Fri 8:00 PM** | `cron(0 20 ? * MON-FRI *)` | `1 → 2` | 50% lower overnight cost while keeping `/crm` online |
| **Sat 12:00 AM** | `cron(0 0 ? * SAT *)` | `1 → 2` | Lower weekend baseline until Monday 9:00 AM |

> **Note on `FARGATE_SPOT`:** `FARGATE_SPOT` is attached to `frappe-crm-cluster` and configured in `docker/appspec.yaml`, while the live service keeps `launch_type = "FARGATE"` to avoid replacing the active demo service (`frappe-crm:8`).

---

## Quick Verification Commands

```bash
# 1. Check ECS Auto Scaling policies (CPU 70% / Memory 75%)
aws application-autoscaling describe-scaling-policies --service-namespace ecs \
  --resource-id service/frappe-crm-cluster/frappe-crm-service --region ap-southeast-2 --output table

# 2. Check Off-Hours Schedule (Asia/Kolkata)
aws application-autoscaling describe-scheduled-actions --service-namespace ecs \
  --resource-id service/frappe-crm-cluster/frappe-crm-service --region ap-southeast-2 --output table

# 3. Check Cluster Capacity Providers (FARGATE + FARGATE_SPOT)
aws ecs describe-clusters --clusters frappe-crm-cluster --region ap-southeast-2 \
  --query "clusters[0].{Providers:capacityProviders,Default:defaultCapacityProviderStrategy}"

# 4. Tear down all AWS resources after review to stop all hourly billing
cd terraform && terraform destroy
```
