# Frappe CRM on AWS ECS Fargate (Blue-Green)

```
git push -> GitHub Actions -> build image -> ECR -> CodeDeploy blue/green -> ECS Fargate behind ALB
                                                                              |
                                                                       CloudWatch logs + alarm
```

## Requirements covered

| # | Requirement | Where |
|---|-------------|-------|
| 1 | Dockerize | `Dockerfile`, `docker/entrypoint.sh`, `healthcheck.sh` |
| 2 | Push to ECR | `.github/workflows/deploy.yml` (repo created in `terraform/main.tf`) |
| 3 | Terraform | `terraform/main.tf`, `variables.tf`, `outputs.tf` |
| 4 | ECS Fargate | `terraform/main.tf` (cluster, task definition, service) |
| 5 | Blue-Green with ALB | two target groups + CodeDeploy (`main.tf`, `deployment/appspec.yaml`) |
| 6 | GitHub Actions | `.github/workflows/deploy.yml` |
| 7 | Health checks + auto rollback | `healthcheck.sh` (container), ALB `/api/method/ping`, CodeDeploy auto-rollback |
| 8 | CloudWatch | logs, alarms, dashboard (see Monitoring) |

## Setup

1. Create infrastructure:
   ```bash
   cd terraform
   terraform init
   terraform apply -var 'db_root_password=CHANGE_ME' -var 'admin_password=CHANGE_ME'
   ```
2. Push the first image (service needs one in ECR):
   ```bash
   ECR=$(terraform output -raw ecr_repository_url)
   aws ecr get-login-password --region ap-south-1 | docker login --username AWS --password-stdin ${ECR%/*}
   docker build -t $ECR:latest ..
   docker push $ECR:latest
   aws ecs update-service --cluster frappe-crm-cluster --service frappe-crm-service --force-new-deployment
   ```
3. Add GitHub secrets `AWS_ACCESS_KEY_ID` and `AWS_SECRET_ACCESS_KEY`. Every push to `main` now deploys.
4. Open `terraform output app_url` (first start takes ~10-15 min). Login: `Administrator` / your admin password, then `/crm`.

## Blue-Green and rollback

CodeDeploy starts the new version (green) next to the old one (blue). Port 80 moves to green only after green passes the ALB health check. If green never becomes healthy, or the unhealthy-hosts alarm fires, the deployment fails and rolls back automatically; users stay on blue. Old tasks are removed 1 minute after success.

## Health checks

- Container: `healthcheck.sh` (curl `/api/method/ping`), every 30s, 600s start period.
- ALB: `/api/method/ping` expects HTTP 200, every 30s.

## Monitoring

- Logs: CloudWatch log group `/ecs/frappe-crm`.
- Alarms: unhealthy hosts for blue and green target groups, ECS CPU > 80%, memory > 80%, ALB 5XX > 10/min.
- Dashboard `frappe-crm`: CPU/memory, requests/5XX, unhealthy hosts (blue and green).
- The two unhealthy-host alarms are attached to CodeDeploy, so an alarm during a deployment rolls it back.

## CI

`terraform validate` runs on every pull request and before every deploy. The deploy job only runs on pushes to `main`.

## Limitation

MariaDB and Redis run as sidecars in the task to keep this simple, so data is not persistent across deployments. Production would use RDS + ElastiCache.
