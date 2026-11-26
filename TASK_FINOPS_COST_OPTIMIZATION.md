# AWS Cost Optimization (FinOps) Documentation — Frappe CRM on ECS Fargate

**Repository:** `PearlThoughts-Intern-DevOps/frappe-crm-devops-internship`  
**Candidate:** Bulbul Das (`dasbulbul215@gmail.com`)  
**Branch:** `task-bulbul-das` (PR `#88` → `main`)  
**AWS Project ID:** `865188471560`  
**Selected AWS Region:** `ap-southeast-2` (Sydney)  

---

## 1. Executive Summary

This document details the **FinOps (Cloud Financial Management)** and **AWS Cost Optimization** practices implemented across the **Frappe CRM ECS Fargate Blue-Green** infrastructure. Every control is codified in **Terraform** (`terraform/`) and **Docker / CodeDeploy** (`docker/`), balancing production availability during business/demo hours with automated waste reduction during idle and off-hours periods.

### FinOps Pillars Covered

| # | FinOps Practice | Primary Mechanism | Implementation File(s) |
|---|---|---|---|
| **1** | **Cost Allocation & Governance Tagging** | Provider-level `default_tags` on every AWS resource | `terraform/provider.tf` |
| **2** | **Dynamic Compute Auto Scaling** | Target tracking on ECS CPU (`70%`) and Memory (`75%`) | `terraform/autoscaling.tf`, `terraform/ecs.tf` |
| **3** | **Off-Hours & Weekend Scheduling** | Scheduled scaling actions in `Asia/Kolkata` timezone | `terraform/autoscaling.tf`, `terraform/variables.tf` |
| **4** | **Fargate Spot Capacity Strategy** | Cluster capacity providers + Blue-Green `CapacityProviderStrategy` | `terraform/ecs.tf`, `docker/appspec.yaml` |
| **5** | **Network & Data-Transfer Optimization** | Single NAT Gateway + Free S3 VPC Gateway Endpoint | `terraform/vpc.tf` |
| **6** | **Database & Cache Right-Sizing** | Graviton (`t4g.micro`) instances + `gp3` storage autoscaling (`20–50 GB`) | `terraform/rds.tf`, `terraform/redis.tf` |
| **7** | **Storage & Log Lifecycle Caps** | ECR image pruning (`7d` untagged / last `15` tagged) + `14d` log retention | `terraform/ecr.tf`, `terraform/cloudwatch.tf` |
| **8** | **Blue-Green & CI/CD Waste Prevention** | `5`-minute Blue termination + `workflow_dispatch`-gated deploys | `terraform/codedeploy.tf`, `.github/workflows/deploy-ecs-bluegreen.yml` |

---

## 2. Detailed FinOps Implementations

### 2.1 Cost-Allocation Tagging (`terraform/provider.tf`)
All Terraform-managed resources automatically inherit uniform cost-allocation tags via the AWS provider `default_tags` block:

```hcl
default_tags {
  tags = {
    Project            = var.project_name       # "frappe-crm"
    Environment        = var.environment        # "prod"
    ManagedBy          = "Terraform"
    DeploymentStrategy = "Blue-Green"
    Application        = "Frappe-CRM"
  }
}
```

**Why this matters:**
- Enables accurate cost filtering, chargeback/showback reporting, and service-level spend tracking in AWS Billing and Cost Management.
- Prevents untagged or orphaned resources from hiding inside shared project spend.

---

### 2.2 ECS Application Auto Scaling (`terraform/autoscaling.tf`, `terraform/ecs.tf`)
Instead of over-provisioning fixed peak capacity 24/7, `frappe-crm-service` is registered as an Application Auto Scaling target (`aws_appautoscaling_target.ecs`) with `min_capacity = 1` and `max_capacity = 4`:

- **CPU Target Tracking (`frappe-crm-cpu-autoscaling`):**
  - Metric: `ECSServiceAverageCPUUtilization`
  - Target: `70.0%`
  - Cooldowns: `scale_out_cooldown = 60s`, `scale_in_cooldown = 300s`
- **Memory Target Tracking (`frappe-crm-memory-autoscaling`):**
  - Metric: `ECSServiceAverageMemoryUtilization`
  - Target: `75.0%`
  - Cooldowns: `scale_out_cooldown = 60s`, `scale_in_cooldown = 300s`
- **Drift Protection (`terraform/ecs.tf`):**
  - `desired_count` is included in `lifecycle { ignore_changes = [task_definition, load_balancer, desired_count, launch_type] }` so Terraform runs never revert Auto Scaling adjustments.

---

### 2.3 Off-Hours & Weekend Scheduled Scaling (`terraform/autoscaling.tf`)
To avoid running full multi-task capacity during nights and weekends, three scheduled scaling actions run in **`Asia/Kolkata` (IST)**:

| Action Name | Schedule (`cron` in `Asia/Kolkata`) | Min Tasks | Max Tasks | Behavior |
|---|---|---|---|---|
| `frappe-crm-scale-out-business-hours` | `cron(0 9 ? * MON-FRI *)` (9:00 AM Mon–Fri) | `2` | `4` | Restores multi-AZ High Availability for active work/demo hours |
| `frappe-crm-scale-in-off-hours` | `cron(0 20 ? * MON-FRI *)` (8:00 PM Mon–Fri) | `1` | `2` | Reduces baseline Fargate compute by 50% overnight while keeping `/crm` online |
| `frappe-crm-scale-in-weekends` | `cron(0 0 ? * SAT *)` (12:00 AM Saturday) | `1` | `2` | Keeps weekend baseline at 1 task until Monday 9:00 AM |

**Design decision (`min = 1` vs `min = 0`):** Keeping `min_capacity = 1` overnight avoids `503 Service Unavailable` errors and ALB unhealthy-host alarm triggers if a user or reviewer opens the application outside business hours, while still cutting baseline Fargate compute in half.

---

### 2.4 Fargate Spot Capacity Providers (`terraform/ecs.tf`, `docker/appspec.yaml`)
- **Cluster Capacity Providers (`aws_ecs_cluster_capacity_providers.main`):**
  - Associates both **`FARGATE`** (On-Demand) and **`FARGATE_SPOT`** with `frappe-crm-cluster`.
  - Default cluster strategy sets `FARGATE` (`base = 1`, `weight = 1`).
- **Blue-Green Spot Mix (`docker/appspec.yaml`):**
  - Configured `CapacityProviderStrategy` for CodeDeploy task sets:
    - `FARGATE`: `Base = 1`, `Weight = 1` (guarantees 1 stable On-Demand task that cannot be Spot-reclaimed)
    - `FARGATE_SPOT`: `Base = 0`, `Weight = 3` (routes secondary and burst-scaled tasks to discounted Spot capacity)
- **Graceful Spot Interruption Handling (`docker/entrypoint.sh`, `terraform/alb.tf`):**
  - `entrypoint.sh` traps `SIGTERM`/`SIGINT` (`shutdown()`) and ALB target groups use `deregistration_delay = 30s`, allowing clean connection draining on Spot reclamation or scale-in.
- **Current Live State Note:** The live `frappe-crm-service` currently remains on `launch_type = "FARGATE"` to avoid destructive service replacement on the active demo environment; `FARGATE_SPOT` is attached at the cluster level and defined in `docker/appspec.yaml`.

---

### 2.5 Network & Data-Transfer Optimization (`terraform/vpc.tf`)
- **Single NAT Gateway (`aws_nat_gateway.nat`):**
  - Uses **1 NAT Gateway** in `public[0]` (`10.1.1.0/24`) rather than deploying one NAT Gateway per Availability Zone, cutting fixed hourly NAT Gateway and Elastic IP overhead in half for this workload tier.
- **Free S3 VPC Gateway Endpoint (`aws_vpc_endpoint.s3` — `vpce-0c962e68c09c5f297`):**
  - Attached a `Gateway` endpoint for `com.amazonaws.ap-southeast-2.s3` directly to private route table `rtb-0aec6c7b4c4045082`.
  - Because Amazon ECR stores container image layers in S3, Fargate tasks in private subnets pull image layers directly via the free Gateway Endpoint instead of incurring per-GB NAT Gateway data-processing fees.
  - Paid VPC Interface Endpoints (e.g., ECR API/DKR, CloudWatch Logs) were intentionally avoided because their per-AZ hourly charges exceed low-volume NAT transfer costs.

---

### 2.6 Database & Cache Right-Sizing (`terraform/rds.tf`, `terraform/redis.tf`)
- **RDS MariaDB (`frappe-crm-db`, engine `mariadb` `10.11`):**
  - Uses ARM64/Graviton **`db.t4g.micro`** rather than larger x86 instances.
  - Uses `gp3` storage starting at **`20 GB`** with storage autoscaling capped at **`max_allocated_storage = 50 GB`**, eliminating upfront over-provisioning.
  - Non-prod/demo settings avoid unnecessary snapshot/insights overhead (`skip_final_snapshot = true`, `backup_retention_period = 0`, `performance_insights_retention_period = 0`).
- **ElastiCache Redis (`frappe-crm-redis`, engine `redis` `7.0`):**
  - Uses ARM64/Graviton **`cache.t4g.micro`** with **`num_cache_nodes = 1`**.
  - Consolidates all three Frappe Redis roles (`REDIS_CACHE_URL`, `REDIS_QUEUE_URL`, `REDIS_SOCKETIO_URL`) onto one right-sized cluster instead of provisioning three separate Redis clusters.

---

### 2.7 Container, Registry & Log Lifecycle Governance
- **Amazon ECR Lifecycle Policy (`terraform/ecr.tf`):**
  - Rule 1: Expire **untagged** images older than **7 days** (cleans up intermediate/superseded builds automatically).
  - Rule 2: Retain at most **15 tagged images** (`v`, `sha-`, `task-`, `latest`), preserving rollback history while capping registry storage.
- **CloudWatch Log Retention (`terraform/cloudwatch.tf`):**
  - Log group `/ecs/frappe-crm` enforces **`retention_in_days = 14`** instead of AWS's default "Never expire", preventing indefinite log accumulation charges.
- **Lean Docker Image (`docker/Dockerfile`):**
  - Installs only `--no-install-recommends` apt packages and cleans `/var/lib/apt/lists/*`.
  - Installs Python packages with `--no-cache-dir`.
  - Strips `redis` and `watch` processes from `Procfile` so containers do not waste Fargate CPU/RAM running redundant local processes.

---

### 2.8 Blue-Green Task Cleanup & CI/CD Guardrails
- **Automatic Blue Task Termination (`terraform/codedeploy.tf`):**
  - `terminate_blue_instances_on_deployment_success` uses `action = "TERMINATE"` after **`termination_wait_time_in_minutes = 5`**, ensuring superseded task sets do not remain running and billing after a Blue-Green cutover succeeds.
- **CI/CD Build & Deploy Gating (`.github/workflows/deploy-ecs-bluegreen.yml`):**
  - Pull requests execute only `lint-and-validate` (`terraform fmt -check`, AppSpec/task-definition checks).
  - `build-and-push` and `deploy-blue-green` are gated behind `workflow_dispatch` (with `deploy_to_aws == true`), avoiding wasteful Docker builds, ECR pushes, and Blue-Green task churn on every documentation or PR commit.

---

## 3. AWS Governance & Teardown Best Practices

- **Project Spend Limits:** Configured/monitored at the project level under **AWS Settings > Billing** (as part of the managed AWS project experience).
- **Post-Demo Idle Cost Prevention:** Because `ALB`, `NAT Gateway`, `RDS`, `ElastiCache`, and at least `1` Fargate task incur hourly charges while active, infrastructure can be cleanly paused or decommissioned after evaluation:
  ```bash
  # Inspect live FinOps controls
  aws application-autoscaling describe-scaling-policies \
    --service-namespace ecs \
    --resource-id service/frappe-crm-cluster/frappe-crm-service \
    --region ap-southeast-2 --output table

  aws application-autoscaling describe-scheduled-actions \
    --service-namespace ecs \
    --resource-id service/frappe-crm-cluster/frappe-crm-service \
    --region ap-southeast-2 --output table

  aws ecs describe-clusters --clusters frappe-crm-cluster --region ap-southeast-2 \
    --query "clusters[0].{CapacityProviders:capacityProviders,DefaultStrategy:defaultCapacityProviderStrategy}"

  aws ec2 describe-vpc-endpoints \
    --filters Name=vpc-id,Values=vpc-0938b3e604c5cf207 \
    --region ap-southeast-2 \
    --query "VpcEndpoints[*].{Id:VpcEndpointId,Service:ServiceName,Type:VpcEndpointType,State:State}"
  ```
  - When the internship review is complete and the environment is no longer needed, running `cd terraform && terraform destroy` removes all billable resources cleanly.

---

## 4. Future Production FinOps Enhancements (Next Phase)
1. **Complete live cutover of `frappe-crm-service` to `capacity_provider_strategy` (`FARGATE` + `FARGATE_SPOT`)** during a planned maintenance window (one-time replacement of the base service created with `launch_type = "FARGATE"`).
2. **Switch Fargate tasks to `ARM64` (Graviton)** (`runtime_platform { cpu_architecture = "ARM64" }`) with multi-arch Docker builds to further lower base On-Demand Fargate compute costs.
3. **Compute Savings Plans / RDS Reserved Instances** once steady-state production baseline utilization is established.
