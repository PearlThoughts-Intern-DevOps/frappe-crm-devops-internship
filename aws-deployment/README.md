# Frappe CRM - AWS ECS Fargate Deployment

## Overview
Infrastructure-as-code and deployment configuration for a proposed Frappe CRM deployment using AWS ECS Fargate, ALB and CodeDeploy blue-green deployments.

## Architecture
- Docker image built using the official Frappe Docker layered Containerfile.
- CRM application declared through apps.json.
- Amazon ECR for image storage.
- Amazon ECS with AWS Fargate.
- Application Load Balancer with blue and green target groups.
- AWS CodeDeploy for blue-green deployments and rollback.
- CloudWatch logs and CPU/memory alarms.
- Terraform for infrastructure provisioning.
- GitHub Actions for CI/CD orchestration.

## Container Image
The Dockerfile follows the official Frappe Docker layered image build approach.
The CRM application is declared in apps.json.
Frappe Framework is configured for version-15 to match the existing development setup.

## Blue-Green Deployment
The planned deployment uses:
1. An ECS service managed by CodeDeploy.
2. Blue and green ALB target groups.
3. A production listener on port 80.
4. CodeDeploy traffic shifting.
5. Automatic rollback configuration.

## Monitoring
- ECS CPU utilization alarm.
- ECS memory utilization alarm.
- CloudWatch log group with seven-day retention.

## Local Validation
- Docker Buildx Dockerfile configuration check passed.
- Terraform formatting passed.
- Terraform initialization with -backend=false passed.
- Terraform validation passed.
- CRM apps.json JSON validation passed.
- Published CRM image inspected; it did not contain the CRM application directory.

## Deployment Status
This configuration has NOT been deployed to AWS.
No AWS resources have been provisioned, no image has been pushed to ECR, and no live ECS or CodeDeploy deployment has been tested.

The following work remains before production deployment:
- Complete Frappe production service architecture.
- Configure persistent database and site-file storage.
- Configure Redis, workers, scheduler and WebSocket services.
- Verify container ports, commands and health-check endpoints.
- Complete and test CodeDeploy AppSpec and validation hooks.
- Complete GitHub Actions AWS authentication and deployment stages.
- Review IAM permissions and networking.
- Test deployment rollback in AWS.

## Cost and Safety
ECS Fargate, ALB, ECR storage, databases and CloudWatch can incur charges.
This configuration has not been applied to AWS. Review costs and obtain budget approval before deployment.
