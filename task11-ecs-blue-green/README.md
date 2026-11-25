\# Task 11 – Frappe CRM ECS Fargate Blue-Green Deployment



\## 1. Project Overview



This project demonstrates deploying Frappe CRM on \*\*Amazon ECS with AWS Fargate\*\*, using an Application Load Balancer (ALB) and AWS CodeDeploy to perform Blue-Green deployments.



The infrastructure is provisioned using Terraform. The container image is hardened and stored in Amazon Elastic Container Registry (ECR). GitHub Actions uses OpenID Connect (OIDC) to authenticate with AWS and initiate deployments without storing long-lived AWS access keys.



\### Project Objectives



\- Build and publish a hardened Frappe CRM Docker image.

\- Store the image in Amazon ECR.

\- Provision AWS infrastructure using Terraform.

\- Run Frappe CRM using ECS Fargate.

\- Configure Blue-Green deployments using AWS CodeDeploy.

\- Route application traffic through an Application Load Balancer.

\- Monitor deployment health using CloudWatch alarms.

\- Automate deployments through GitHub Actions and AWS OIDC.

\- Capture deployment and security evidence.



\## 2. Architecture Diagram



The following diagram illustrates the AWS infrastructure and deployment workflow.



```mermaid

flowchart TB

&#x20;   DEV\["Developer"] --> GH\["GitHub Repository"]

&#x20;   GH --> GHA\["GitHub Actions Workflow"]

&#x20;   GHA --> OIDC\["AWS IAM OIDC Role"]

&#x20;   OIDC --> CD\["AWS CodeDeploy"]



&#x20;   DEV --> BUILD\["Docker Build"]

&#x20;   BUILD --> SCAN\["Container Security Scanning"]

&#x20;   SCAN --> ECR\["Amazon ECR<br/>Frappe CRM Image"]



&#x20;   ECR --> ECS\["Amazon ECS Cluster<br/>AWS Fargate"]



&#x20;   ECS --> BLUE\["Blue Task Set"]

&#x20;   ECS --> GREEN\["Green Task Set"]

&#x20;   CD --> BLUE

&#x20;   CD --> GREEN



&#x20;   USERS\["Application Users"] --> ALB\["Application Load Balancer"]

&#x20;   ALB --> TG1\["Target Group 1"]

&#x20;   ALB --> TG2\["Target Group 2"]

&#x20;   TG1 --> BLUE

&#x20;   TG2 --> GREEN



&#x20;   BLUE --> RDS\["Amazon RDS<br/>MariaDB"]

&#x20;   GREEN --> RDS



&#x20;   BLUE --> REDIS\["Amazon ElastiCache<br/>Redis"]

&#x20;   GREEN --> REDIS



&#x20;   BLUE --> EFS\["Amazon EFS<br/>Persistent Storage"]

&#x20;   GREEN --> EFS



&#x20;   SECRETS\["AWS Secrets Manager"] --> BLUE

&#x20;   SECRETS --> GREEN



&#x20;   BLUE --> CW\["Amazon CloudWatch"]

&#x20;   GREEN --> CW

&#x20;   ALB --> CW

&#x20;   CW --> CD



&#x20;   TF\["Terraform"] -. "Provisions infrastructure" .-> ECS

&#x20;   TF -.-> ALB

&#x20;   TF -.-> RDS

&#x20;   TF -.-> REDIS

&#x20;   TF -.-> EFS

&#x20;   TF -.-> CD

```



\### Blue-Green Deployment Workflow



1\. A hardened Docker image is built and published to Amazon ECR.

2\. GitHub Actions authenticates with AWS through OIDC.

3\. The workflow registers a new ECS task definition revision.

4\. CodeDeploy creates a new task set alongside the existing task set.

5\. The Application Load Balancer routes traffic to the selected task set.

6\. CloudWatch monitors application and target health.

7\. After successful validation, the new task set becomes the primary task set.

8\. Configured deployment failures can trigger automatic rollback.



\## 3. AWS Environment



| Component | Configuration |

|---|---|

| AWS Region | `ap-southeast-2` (Sydney) |

| ECS Cluster | `frappe-crm-task11-dev-cluster` |

| ECS Web Service | `frappe-crm-task11-dev-web` |

| ECS Worker Service | `frappe-crm-task11-dev-worker` |

| ECS Scheduler Service | `frappe-crm-task11-dev-scheduler` |

| ECS WebSocket Service | `frappe-crm-task11-dev-websocket` |

| CodeDeploy Application | `frappe-crm-task11-dev-app` |

| CodeDeploy Deployment Group | `frappe-crm-task11-dev-blue-green` |

| ECR Repository | `frappe-crm` |

| ECR Image Tag | `15-hardened-2-amd64` |

| Terraform Resources Created | 64 |



\### Application Endpoint



```text

http://frappe-crm-task11-dev-alb-1351892118.ap-southeast-2.elb.amazonaws.com

```



Application health-check endpoint:



```text

/api/method/ping

```



Expected response:



```json

{"message":"pong"}

```



\## 4. Project Structure



```text

task11-ecs-blue-green/

│

├── README.md

├── appspec.yaml

│

├── docker/

│   ├── apps.json

│   ├── Dockerfile.security

│   └── entrypoint.sh

│

├── docs/

│   └── IMAGE-SECURITY-REPORT.md

│

├── screenshots/

│   ├── 01-frappe-login.png

│   ├── 02-frappe-dashboard.png

│   ├── 03-ecs-cluster.png

│   ├── 04-ecs-services.png

│   ├── 05-ecs-fargate-running-task.png

│   ├── 06-codedeploy-success.png

│   ├── 07-blue-green-traffic.png

│   ├── 08-alb-listener.png

│   ├── 09-alb-healthy-targets.png

│   ├── 10-cloudwatch-alarms.png

│   ├── 11-ecr-image.png

│   └── 12-security-scan.png

│

└── terraform/

&#x20;   ├── .gitignore

&#x20;   ├── .terraform.lock.hcl

&#x20;   ├── codedeploy.tf

&#x20;   ├── database.tf

&#x20;   ├── ecs.tf

&#x20;   ├── ecs\_processes.tf

&#x20;   ├── ecs\_services.tf

&#x20;   ├── ecs\_tasks.tf

&#x20;   ├── github\_oidc.tf

&#x20;   ├── iam.tf

&#x20;   ├── load\_balancer.tf

&#x20;   ├── monitoring.tf

&#x20;   ├── network.tf

&#x20;   ├── outputs.tf

&#x20;   ├── redis.tf

&#x20;   ├── secrets.tf

&#x20;   ├── security\_groups.tf

&#x20;   ├── storage.tf

&#x20;   ├── variables.tf

&#x20;   └── versions.tf

```



\*\*Note:\*\* Terraform state files, `.tfvars` files, plans, provider binaries and local backup files are excluded from Git for security.



\## 5. Tools and Technologies



\- AWS ECS and AWS Fargate

\- Amazon ECR

\- AWS CodeDeploy

\- Application Load Balancer

\- Amazon RDS MariaDB

\- Amazon ElastiCache Redis

\- Amazon EFS

\- AWS Secrets Manager

\- Amazon CloudWatch

\- Terraform

\- Docker

\- GitHub Actions

\- GitHub OIDC

\- Trivy

\- PowerShell and AWS CloudShell



\## 6. Infrastructure and Deployment



\### Infrastructure Provisioning



Terraform was used to provision the AWS infrastructure, including:



\- VPC, subnets and networking components.

\- Security groups and IAM roles.

\- ECS cluster, services and task definitions.

\- Application Load Balancer and target groups.

\- RDS MariaDB database.

\- ElastiCache Redis.

\- EFS persistent storage.

\- AWS Secrets Manager.

\- CodeDeploy application and deployment group.

\- CloudWatch log groups and alarms.

\- GitHub OIDC integration.



The Terraform deployment completed successfully:



```text

Apply complete! Resources: 64 added, 0 changed, 0 destroyed.

```



\### Containerization



The Frappe CRM image was built using:



`docker/Dockerfile.security`



The project also uses:



`docker/entrypoint.sh`



The image was built for Linux AMD64 and published to Amazon ECR.



\### ECS Fargate Deployment



The application runs through ECS Fargate services:



\- Web

\- Worker

\- Scheduler

\- WebSocket



The ECS web service uses the `CODE\_DEPLOY` deployment controller to support Blue-Green deployments.



\### Blue-Green Deployment



AWS CodeDeploy manages the Blue and Green task sets.



During deployment:



\- A new task set is created.

\- The ALB routes traffic according to the deployment configuration.

\- CloudWatch alarms monitor deployment health.

\- The new task set becomes primary after successful deployment.

\- Automatic rollback is enabled for configured deployment failure conditions.



\### CI/CD Automation



GitHub Actions automates the deployment workflow.



The workflow is located at:



`.github/workflows/task11-deploy.yml`



It uses:



\- GitHub Actions manual workflow dispatch.

\- AWS IAM OIDC authentication.

\- ECS task definition registration.

\- CodeDeploy deployment creation.

\- Deployment status monitoring.



No long-lived AWS access keys are required when OIDC is configured correctly.



\## 7. Security Implementation



\### Container Security



\- Used a dedicated hardened Dockerfile.

\- Used a dedicated container entrypoint.

\- Built an AMD64 Linux image for ECS Fargate.

\- Performed container image vulnerability scanning.

\- Documented security scan findings.



\### AWS Security



\- Used IAM roles for AWS service access.

\- Configured GitHub OIDC instead of embedding AWS access keys in the workflow.

\- Stored application secrets in AWS Secrets Manager.

\- Used security groups to control network access.

\- Used private networking for application dependencies where configured.

\- Kept Terraform state and variable files out of Git.



\### Deployment Safety



\- Configured CodeDeploy Blue-Green deployment.

\- Configured CloudWatch deployment alarms.

\- Enabled automatic rollback for configured deployment failure conditions.



\### ECR Image Security Scan Results



| Severity | Findings |

|---|---:|

| Critical | 0 |

| High | 18 |

| Medium | 31 |

| Low | 7 |

| Undefined | 1 |



The image scan completed successfully, but vulnerabilities were identified and documented for remediation.



Refer to `docs/IMAGE-SECURITY-REPORT.md` for the detailed security report.



\## 8. Deployment Results



The deployment was successfully completed and verified.



| Verification | Result |

|---|---|

| Terraform infrastructure provisioning | 64 resources created |

| ECR image | Published |

| ECS Fargate web service | Running |

| ECS worker service | Configured |

| ECS scheduler service | Configured |

| ECS WebSocket service | Configured |

| CodeDeploy deployment | Succeeded |

| Blue-Green traffic shift | Verified |

| ALB application health | HTTP 200 |

| Frappe CRM login | Verified |

| CloudWatch alarms | Configured |

| ECR image scan | Completed |



\### CodeDeploy Deployment



```text

Deployment ID: d-6XXJJKTZL

Status: Succeeded

```



\### Application Health



The application health endpoint returned:



```text

HTTP/1.1 200 OK

{"message":"pong"}

```



\### Important Deployment Detail



CodeDeploy can swap target-group roles during a successful deployment. The actual traffic-serving task set should be identified using its `PRIMARY` status and traffic weight, rather than relying only on target-group names.



\## 9. Screenshots and Evidence



The following screenshots are included in the `screenshots/` folder:



| Screenshot | Evidence |

|---|---|

| `01-frappe-login.png` | Frappe CRM login |

| `02-frappe-dashboard.png` | Frappe CRM dashboard |

| `03-ecs-cluster.png` | ECS cluster |

| `04-ecs-services.png` | ECS services |

| `05-ecs-fargate-running-task.png` | Running Fargate task |

| `06-codedeploy-success.png` | Successful CodeDeploy deployment |

| `07-blue-green-traffic.png` | Blue-Green traffic distribution |

| `08-alb-listener.png` | ALB listener configuration |

| `09-alb-healthy-targets.png` | Healthy ALB targets |

| `10-cloudwatch-alarms.png` | CloudWatch alarms |

| `11-ecr-image.png` | ECR image |

| `12-security-scan.png` | Image security scan |



\## 10. Cost and Cleanup



This project provisions billable AWS resources, including:



\- Application Load Balancer.

\- ECS Fargate tasks.

\- RDS MariaDB.

\- ElastiCache Redis.

\- EFS.

\- NAT and networking resources.

\- CloudWatch logs and metrics.

\- Secrets Manager.



After evidence collection and project validation, Terraform-managed infrastructure can be removed to avoid ongoing charges.



\*\*Important:\*\* Do not run `terraform destroy` until deployment evidence has been saved and cleanup has been explicitly approved. Verify that the ECR repository and image are not Terraform-managed resources before destroying the infrastructure.



The ECR repository `frappe-crm` and image tag `15-hardened-2-amd64` are intended to be retained.



\## 11. Learning Outcomes



Through this project, the following practical skills were demonstrated:



\- Building and publishing Docker images.

\- Container hardening and vulnerability scanning.

\- Provisioning cloud infrastructure with Terraform.

\- Deploying containerized applications using ECS Fargate.

\- Configuring ALB listeners and target groups.

\- Implementing Blue-Green deployment with CodeDeploy.

\- Configuring CloudWatch monitoring and deployment alarms.

\- Automating AWS deployment through GitHub Actions.

\- Using GitHub OIDC for secure AWS authentication.

\- Verifying application health and deployment status.

\- Capturing technical evidence and documenting cloud infrastructure.



\## 12. Final Project Summary



This project demonstrates an end-to-end deployment of Frappe CRM on AWS using infrastructure as code, containerization, managed container orchestration, Blue-Green deployment, monitoring and CI/CD automation.



The application was deployed successfully, the CodeDeploy deployment completed with a `Succeeded` status, and the ALB health endpoint returned HTTP 200 with a `pong` response.



The ECR image scan completed and its findings were documented for further remediation.
