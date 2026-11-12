# Frappe CRM Deployment on Kubernetes (Amazon EKS)

## Project Overview

This project demonstrates the deployment of Frappe CRM on Kubernetes using Amazon Elastic Kubernetes Service (EKS).

The application runs in a Kubernetes environment with MariaDB as the database and Redis as the caching and queue service. A Kubernetes LoadBalancer Service exposes the application externally.

## Architecture

The deployment consists of the following components:

- **Amazon EKS:** Managed Kubernetes control plane.
- **Worker Nodes:** EC2 instances that run Kubernetes workloads.
- **Frappe Application:** Runs Frappe Framework v15 with the CRM application installed.
- **MariaDB:** Database service for storing application data.
- **Redis:** Provides caching and queue services.
- **Kubernetes Services:** Enable communication between application components and external access.
- **AWS LoadBalancer:** Exposes the Frappe application through an external DNS endpoint.


## Technology Stack

| Technology | Purpose |
|---|---|
| Amazon EKS | Kubernetes orchestration |
| Amazon EC2 | Worker node infrastructure |
| Kubernetes | Container orchestration |
| Frappe Framework v15 | Application framework |
| Frappe CRM | CRM application |
| MariaDB | Database |
| Redis | Cache and queue |
| kubectl | Kubernetes cluster management |
| AWS LoadBalancer | External application access |
| Linux | Server environment |

## Kubernetes Components

The deployment uses:

- **Pods:** Run the Frappe, MariaDB and Redis workloads.
- **Deployments:** Manage application and dependency pods.
- **Services:** Provide internal communication and external access.
- **ConfigMaps:** Store non-sensitive configuration.
- **Secrets:** Supply sensitive application configuration.

## Deployment Process

1. Created an Amazon EKS cluster.
2. Configured worker nodes and Kubernetes access.
3. Installed and configured `kubectl` and `eksctl`.
4. Created the `frappe-crm` Kubernetes namespace.
5. Deployed MariaDB and Redis.
6. Configured the Frappe initialization script.
7. Created the Frappe v15 bench environment.
8. Created the `crm.localhost` site.
9. Installed the Frappe CRM application.
10. Configured the Kubernetes LoadBalancer Service.
11. Verified application connectivity through the external LoadBalancer DNS endpoint.

## Application Verification

The following checks were performed:

- Frappe pod reached `1/1 Running`.
- MariaDB pod reached `1/1 Running`.
- Redis pod reached `1/1 Running`.
- Application initialization and CRM installation completed.
- HTTP request through the AWS LoadBalancer returned status `200`.
- Frappe CRM login page was accessible through the external endpoint.
- CRM interface was opened in the browser.

## Architecture:
<frappe crm diagram.png>

## Important Notes and Limitations

- This implementation was deployed on Amazon EKS, not Minikube.
- The Frappe application currently uses `bench start`, which is intended for development and demonstration rather than production deployment.
- Persistent volume configuration and database recovery have not yet been verified.
- Production deployment would require additional work on persistent storage, application serving, security, monitoring and high availability.
- Sensitive credentials must be supplied through Kubernetes Secrets and must not be committed to the repository.

## Learning Outcomes

- Understanding Kubernetes architecture and workloads.
- Deploying a multi-component application on Amazon EKS.
- Configuring Kubernetes Deployments and Services.
- Managing application configuration and credentials.
- Integrating AWS LoadBalancer with Kubernetes.
- Troubleshooting pods and application connectivity.