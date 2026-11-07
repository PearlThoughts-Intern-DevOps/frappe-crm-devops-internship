# Task 4: Cloud Platform Exploration

**Platforms:** AWS | Microsoft Azure | Google Cloud Platform (GCP) | Cloudflare  
**Focus:** Key services, their purpose, practical usage and DevOps relevance

---

## 1. Introduction

Cloud platforms provide computing, storage, networking, databases, security and application services over the internet. Organizations use them to host applications, store data, manage infrastructure and scale services without owning all the physical hardware.

This document explores four platforms:

1. **Amazon Web Services (AWS)** – a broad cloud platform offering infrastructure, application, database, networking and DevOps services.
2. **Microsoft Azure** – Microsoft's cloud platform, commonly used with Microsoft enterprise technologies and hybrid environments.
3. **Google Cloud Platform (GCP)** – Google's cloud platform, with services for infrastructure, Kubernetes, data analytics and AI.
4. **Cloudflare** – a platform focused on DNS, content delivery, application security and edge computing.

The goal is to understand what important services do, where they are used and how they support application development and DevOps.

## 2. Cloud Computing Basics

### 2.1 Service models

| Model | Meaning | Example |
|---|---|---|
| IaaS | Infrastructure as a Service: provides virtual machines, networks and storage. The customer manages much of the operating system and application environment. | AWS EC2, Azure Virtual Machines, Google Compute Engine |
| PaaS | Platform as a Service: provides a managed application platform so developers can focus more on application code. | Azure App Service, Google App Engine |
| SaaS | Software as a Service: provides a complete application over the internet. | Microsoft 365, Gmail |

### 2.2 Important concepts

- **Region:** A geographical area where a cloud provider operates infrastructure.
- **Availability Zone:** An isolated location within a region, used to improve application availability.
- **Virtual Machine (VM):** A software-based computer that runs an operating system.
- **Container:** A packaged application and its dependencies.
- **Kubernetes:** A platform for deploying and managing containerized applications.
- **IAM:** Identity and Access Management; controls who can access cloud resources and what they can do.
- **VPC/VNet:** A logically isolated cloud network.
- **Load balancer:** Distributes incoming traffic across application servers or services.
- **CI/CD:** Automated processes to build, test and deploy application changes.
- **Infrastructure as Code (IaC):** Managing infrastructure through configuration files and code, for example with Terraform.

## 3. Amazon Web Services (AWS)

### 3.1 Overview

Amazon Web Services (AWS) is a cloud platform that provides services for compute, storage, databases, networking, security, monitoring and application deployment. It is used to host websites, APIs, enterprise applications and cloud-native workloads.

### 3.2 Important AWS services

| Category | Service | Purpose and common usage |
|---|---|---|
| Compute | **Amazon EC2** (Elastic Compute Cloud) | Provides virtual servers. Used to host applications, web servers, development environments and workloads that need operating-system control. |
| Compute | **AWS Lambda** | Runs code without managing servers. Used for event-driven tasks, automation and APIs. |
| Containers | **Amazon ECS** (Elastic Container Service) | Runs and manages containers using AWS-native orchestration. |
| Containers | **Amazon EKS** (Elastic Kubernetes Service) | Managed Kubernetes service used to deploy and operate containerized applications. |
| Storage | **Amazon S3** (Simple Storage Service) | Object storage for files, backups, logs, static website content and build artifacts. |
| Storage | **Amazon EBS** (Elastic Block Store) | Persistent block storage commonly attached to EC2 instances. |
| Database | **Amazon RDS** (Relational Database Service) | Managed relational databases such as PostgreSQL and MySQL. |
| Database | **Amazon DynamoDB** | Managed NoSQL database for key-value and document data. |
| Networking | **Amazon VPC** (Virtual Private Cloud) | Creates an isolated network with subnets, route tables and security controls. |
| Networking | **Elastic Load Balancing** | Distributes incoming traffic across healthy application targets. |
| Networking | **Amazon Route 53** | DNS service used to route domain names to application endpoints. |
| Security | **AWS IAM** | Manages users, roles and permissions. Supports least-privilege access. |
| Security | **AWS Secrets Manager** | Stores and manages application secrets such as database credentials and API keys. |
| DevOps | **Amazon ECR** (Elastic Container Registry) | Stores Docker and other supported container images. |
| DevOps | **AWS CodeBuild / CodePipeline** | Provides build and pipeline services for CI/CD workflows. |
| Monitoring | **Amazon CloudWatch** | Collects metrics and logs and supports dashboards and alarms. |
| Auditing | **AWS CloudTrail** | Records account and API activity for auditing and investigation. |

### 3.3 Example DevOps usage

A developer pushes code to GitHub. GitHub Actions can run tests, build a Docker image and push it to Amazon ECR. The pipeline can then deploy the image to Amazon EKS or ECS. CloudWatch can be used to monitor application logs and metrics, while IAM roles control access to AWS resources.

### 3.4 AWS billing and pricing

AWS generally uses usage-based pricing. Costs depend on the service, region, resource size, runtime and data transferred.

- **EC2:** Instance type, operating system and running time.
- **S3:** Stored data, requests, retrieval and data transfer.
- **EKS:** Applicable cluster charges, worker compute, storage, load balancers and networking.
- **RDS:** Database size, running time, storage and backups.
- **CloudWatch:** Metrics, log ingestion, retention and related features.

AWS offers options such as On-Demand, Savings Plans, Reserved Instances and Spot Instances for eligible services. Use the [AWS Pricing Calculator](https://calculator.aws/) to estimate costs. Review [AWS Pricing](https://aws.amazon.com/pricing/) for current rates.

**DevOps consideration:** Stop or delete unused lab resources, remove unattached storage, set budgets and review billing after each exercise.

### 3.5 AWS documentation and learning

- [AWS Documentation](https://docs.aws.amazon.com/)
- [AWS Skill Builder](https://skillbuilder.aws/)
- [AWS Pricing Calculator](https://calculator.aws/)
- [AWS Well-Architected Framework](https://aws.amazon.com/architecture/well-architected/)

---

## 4. Microsoft Azure

### 4.1 Overview

Microsoft Azure is Microsoft's cloud computing platform. It provides services for virtual machines, application hosting, containers, storage, databases, networking, identity, security and DevOps. It is commonly used by organizations that work with Microsoft technologies and hybrid infrastructure.

### 4.2 Important Azure services

| Category | Service | Purpose and common usage |
|---|---|---|
| Compute | **Azure Virtual Machines** | Provides Windows or Linux virtual servers for applications and workloads. |
| Compute | **Azure App Service** | Managed hosting for web applications and APIs. |
| Compute | **Azure Functions** | Runs event-driven code without managing servers. |
| Containers | **Azure Kubernetes Service (AKS)** | Managed Kubernetes service for containerized applications. |
| Containers | **Azure Container Apps** | Runs containerized applications and microservices with managed infrastructure. |
| Storage | **Azure Blob Storage** | Object storage for files, backups, logs and unstructured data. |
| Storage | **Azure Files** | Managed file shares that can be accessed by supported systems. |
| Database | **Azure SQL Database** | Managed relational database service based on SQL Server technology. |
| Database | **Azure Cosmos DB** | Globally distributed NoSQL database service. |
| Networking | **Azure Virtual Network (VNet)** | Provides private networking, subnets and network isolation. |
| Networking | **Azure Load Balancer** | Distributes network traffic across backend resources. |
| Networking | **Azure Application Gateway** | Web traffic load balancing with application-layer routing and optional WAF. |
| Networking | **Azure DNS** | Hosts DNS domains and records. |
| Identity | **Microsoft Entra ID** | Manages identities, authentication and access to applications and resources. |
| Security | **Azure Key Vault** | Stores secrets, keys and certificates. |
| DevOps | **Azure DevOps** | Provides Repos, Boards, Pipelines and testing-related capabilities. |
| DevOps | **Azure Container Registry (ACR)** | Stores and manages container images. |
| Monitoring | **Azure Monitor** | Collects and analyzes monitoring data from applications and infrastructure. |
| Monitoring | **Application Insights** | Monitors application performance, requests, failures and dependencies. |

### 4.3 Example DevOps usage

A team can store source code in GitHub or Azure Repos and use GitHub Actions or Azure Pipelines to test and build a Docker image. The image is pushed to Azure Container Registry and deployed to AKS. Azure Key Vault can store application secrets, while Azure Monitor and Application Insights help track application health and performance.

### 4.4 Azure billing and pricing

Azure pricing depends on the service, region, configuration and usage.

- **Virtual Machines:** VM size, operating system, runtime and disks.
- **Blob Storage:** Stored capacity, access tier, operations and data transfer.
- **AKS:** Underlying worker nodes, disks, networking, load balancers and any applicable cluster tier or features.
- **Azure SQL:** Compute tier, storage, backup and availability configuration.
- **Azure Monitor:** Data ingestion, retention and selected monitoring features.

Azure offers pay-as-you-go pricing, reservations and savings plans for eligible services. Azure Spot Virtual Machines use spare capacity and may be evicted. Use the [Azure Pricing Calculator](https://azure.microsoft.com/pricing/calculator/) and check [Azure Pricing](https://azure.microsoft.com/pricing/) for current rates.

**DevOps consideration:** Use resource groups and tags to organize resources, configure budgets and remove unused development resources.

### 4.5 Azure documentation and learning

- [Azure Documentation](https://learn.microsoft.com/azure/)
- [Microsoft Learn – Azure Training](https://learn.microsoft.com/training/azure/)
- [Azure Pricing Calculator](https://azure.microsoft.com/pricing/calculator/)
- [Azure Architecture Center](https://learn.microsoft.com/azure/architecture/)

---

## 5. Google Cloud Platform (GCP)

### 5.1 Overview

Google Cloud Platform (GCP) provides cloud infrastructure and managed services for compute, storage, databases, networking, containers, analytics and artificial intelligence. It is known for Kubernetes, data analytics and Google's global infrastructure.

### 5.2 Important GCP services

| Category | Service | Purpose and common usage |
|---|---|---|
| Compute | **Compute Engine** | Provides virtual machines for applications and infrastructure workloads. |
| Compute | **Cloud Run** | Runs containerized applications on a managed serverless platform. |
| Compute | **Cloud Functions** | Runs event-driven functions for automation and application tasks. |
| Containers | **Google Kubernetes Engine (GKE)** | Managed Kubernetes service for deploying and managing containers. |
| Storage | **Cloud Storage** | Object storage for files, backups, logs and application data. |
| Storage | **Persistent Disk** | Block storage for virtual machine workloads. |
| Database | **Cloud SQL** | Managed relational databases including supported MySQL, PostgreSQL and SQL Server engines. |
| Database | **Firestore** | NoSQL document database for application data. |
| Database | **Cloud Spanner** | Globally distributed relational database. |
| Analytics | **BigQuery** | Data warehouse for analyzing large datasets using SQL. |
| Networking | **Virtual Private Cloud (VPC)** | Provides cloud networking, subnets and network controls. |
| Networking | **Cloud Load Balancing** | Distributes application traffic across backends. |
| Networking | **Cloud DNS** | Hosts DNS zones and records. |
| Security | **Cloud IAM** | Controls access to Google Cloud resources through roles and permissions. |
| Security | **Secret Manager** | Stores application secrets and credentials. |
| DevOps | **Cloud Build** | Builds and tests applications and container images. |
| DevOps | **Artifact Registry** | Stores container images and software packages. |
| DevOps | **Cloud Deploy** | Manages delivery and releases to supported deployment targets. |
| Monitoring | **Cloud Monitoring** | Collects metrics and provides dashboards and alerting. |
| Monitoring | **Cloud Logging** | Collects, stores and analyzes logs. |
| AI/ML | **Vertex AI** | Provides tools and services to build, train and deploy machine-learning and AI applications. |

### 5.3 Example DevOps usage

A GitHub Actions or Cloud Build pipeline can test application code, build a Docker image and push it to Artifact Registry. The image can be deployed to GKE or Cloud Run. Cloud IAM and service identities control access, Secret Manager stores credentials, and Cloud Monitoring and Cloud Logging help operate the application.

### 5.4 GCP billing and pricing

GCP generally charges according to resource usage, service configuration and region.

- **Compute Engine:** Machine type, runtime, disks and network usage.
- **GKE:** Applicable cluster management fees, worker nodes or Autopilot resources, storage and networking.
- **Cloud Storage:** Stored capacity, operations, storage class and data transfer.
- **Cloud SQL:** Compute, storage, backups and availability configuration.
- **BigQuery:** Query processing or selected capacity model, plus storage.
- **Cloud Logging:** Log ingestion and retention.

GCP offers pay-as-you-go pricing, committed-use discounts and Spot VMs for eligible workloads. Some products have free usage allowances, and eligible new customers may receive trial credits. These do not make every connected resource free.

Use the [Google Cloud Pricing Calculator](https://cloud.google.com/products/calculator) and check [Google Cloud Pricing](https://cloud.google.com/pricing) for current rates.

**DevOps consideration:** Set budgets and alerts, use labels to organize resources, right-size VMs and Kubernetes workloads, and review billing data regularly.

### 5.5 GCP documentation and learning

- [Google Cloud Documentation](https://cloud.google.com/docs)
- [Google Cloud Skills Boost](https://www.cloudskillsboost.google/)
- [Google Cloud Pricing Calculator](https://cloud.google.com/products/calculator)
- [Google Cloud Architecture Center](https://cloud.google.com/architecture)
- [GKE Documentation](https://cloud.google.com/kubernetes-engine/docs)

---

## 6. Cloudflare

### 6.1 Overview

Cloudflare is a global network and developer platform focused on DNS, content delivery, application security and edge computing. It is often used together with AWS, Azure or GCP to improve application performance and protect applications exposed to the internet.

Cloudflare is different from the three major cloud platforms: it is not a like-for-like provider of general-purpose virtual machines or managed Kubernetes clusters.

### 6.2 Important Cloudflare services

| Category | Service | Purpose and common usage |
|---|---|---|
| DNS | **Cloudflare DNS** | Hosts DNS records and directs domain traffic to application endpoints. |
| Performance | **CDN** | Caches content at edge locations to improve delivery speed and reduce requests to the origin server. |
| Performance | **Caching** | Controls which content is cached and how long it is retained. |
| Traffic | **Load Balancing** | Routes traffic between origins and can use health checks to identify unhealthy endpoints. |
| Security | **WAF** (Web Application Firewall) | Filters malicious web requests and helps protect web applications. |
| Security | **DDoS Protection** | Helps protect applications from distributed denial-of-service attacks. |
| Security | **SSL/TLS** | Provides settings and certificate options for secure HTTPS connections. |
| Security | **Rate Limiting** | Limits request rates to help protect APIs and applications. |
| Zero Trust | **Cloudflare Access** | Controls access to internal applications based on identity and policy. |
| Connectivity | **Cloudflare Tunnel** | Connects private services to Cloudflare through an outbound tunnel, avoiding the need to expose an inbound service port directly. |
| Developer platform | **Workers** | Runs application code at Cloudflare's edge for APIs and request processing. |
| Developer platform | **Pages** | Builds and hosts web applications from Git-based workflows. |
| Storage | **R2** | Object storage used for files and application data. |
| Storage/data | **Workers KV / D1** | Provides key-value storage and a serverless SQL database for supported application patterns. |

### 6.3 Example DevOps usage

An application may run on AWS, Azure or GCP while Cloudflare manages its public DNS, CDN and WAF. Cloudflare can cache static content, apply security rules and route requests to the application origin. Developers can also use Workers or Pages for suitable edge and web application workloads.

### 6.4 Cloudflare billing and pricing

Cloudflare offers different plans and usage-based pricing depending on the product.

- **Website plans:** Plan level and included features.
- **Workers:** Requests and compute usage, subject to plan allowances.
- **R2:** Storage and operations; review the current pricing terms for applicable retrieval and transfer charges.
- **Pages:** Plan limits and applicable build or related usage.
- **Load Balancing:** Plan and usage metrics.
- **Additional security products:** Pricing depends on the selected product and plan.

Cloudflare provides free and paid plans for selected products. A free plan does not mean every Cloudflare product or advanced feature is free. Use the official [Cloudflare Plans](https://www.cloudflare.com/plans/) and [Developer Pricing](https://developers.cloudflare.com/) pages to check current terms.

**DevOps consideration:** Monitor request volume, storage and operation usage. Review plan limits and paid features before enabling them for a production application.

### 6.5 Cloudflare documentation and learning

- [Cloudflare Developer Documentation](https://developers.cloudflare.com/)
- [Cloudflare Learning Center](https://www.cloudflare.com/learning/)
- [Cloudflare Plans and Pricing](https://www.cloudflare.com/plans/)
- [Cloudflare R2 Documentation](https://developers.cloudflare.com/r2/)
- [Cloudflare Workers Documentation](https://developers.cloudflare.com/workers/)

---

## 7. Quick Comparison of the Four Platforms

| Area | AWS | Microsoft Azure | GCP | Cloudflare |
|---|---|---|---|---|
| Main focus | Broad cloud infrastructure and managed services | Cloud services and Microsoft enterprise integration | Cloud infrastructure, Kubernetes, analytics and AI | DNS, CDN, application security and edge computing |
| Virtual machines | EC2 | Azure Virtual Machines | Compute Engine | No general-purpose VM equivalent |
| Managed Kubernetes | EKS | AKS | GKE | Not a direct equivalent |
| Object storage | S3 | Blob Storage | Cloud Storage | R2 |
| Serverless compute | Lambda | Azure Functions | Cloud Functions / Cloud Run | Workers |
| Container registry | ECR | ACR | Artifact Registry | Not a direct equivalent |
| Monitoring | CloudWatch | Azure Monitor | Cloud Monitoring | Cloudflare analytics and product observability |
| CI/CD options | CodePipeline, CodeBuild, GitHub Actions | Azure Pipelines, GitHub Actions | Cloud Build, Cloud Deploy, GitHub Actions | Git-based Pages and Workers workflows |

The services listed are comparable by use case, but they may differ in features, architecture, availability and pricing.

## 8. DevOps Perspective: How the Platforms Fit into a Project

Consider a simple application that is stored in GitHub, packaged as a Docker image and deployed to a cloud platform.

A typical workflow is:

1. A developer pushes code to GitHub.
2. A CI/CD pipeline starts automatically.
3. The pipeline installs dependencies and runs tests.
4. It builds a Docker image.
5. The image is pushed to a container registry.
6. The application is deployed to a container service or Kubernetes cluster.
7. Secrets and permissions are managed securely.
8. Monitoring and logging are configured.
9. The team checks application health and handles failures or rollbacks.

| DevOps requirement | AWS | Azure | GCP | Cloudflare |
|---|---|---|---|---|
| Run containers | ECS / EKS | Container Apps / AKS | Cloud Run / GKE | Workers and other edge offerings for suitable workloads |
| Store images | ECR | ACR | Artifact Registry | Not a general-purpose equivalent |
| Store application files | S3 | Blob Storage | Cloud Storage | R2 |
| Manage access | IAM | Microsoft Entra ID and Azure RBAC | Cloud IAM | Access for protected application access |
| Store secrets | Secrets Manager | Key Vault | Secret Manager | Workers secrets |
| Monitor workloads | CloudWatch | Azure Monitor | Cloud Monitoring | Product-specific analytics and observability |

### Security and operational practices

- Use least-privilege permissions.
- Do not commit passwords, API keys or cloud credentials to Git.
- Prefer short-lived credentials and workload identity integrations where supported.
- Use private networking where appropriate.
- Configure health checks and monitoring.
- Keep backups and test recovery procedures.
- Review resource usage and billing.
- Remove temporary resources after completing labs.

## 9. Learning Resources and Practical Exploration

The following activities can be used to explore the platforms and understand their services.

### AWS

- Read the EC2, S3, VPC, IAM, EKS and CloudWatch documentation.
- Identify how a virtual machine, object storage bucket and private network are configured.
- Review how ECR and EKS fit into a container deployment.
- Open the AWS Pricing Calculator and estimate a small VM deployment.

### Microsoft Azure

- Read the Virtual Machines, Blob Storage, VNet, Entra ID, AKS and Azure Monitor documentation.
- Explore how a resource group organizes cloud resources.
- Review how ACR connects to AKS.
- Open the Azure Pricing Calculator and estimate a small deployment.

### GCP

- Read the Compute Engine, Cloud Storage, VPC, IAM, GKE and Cloud Monitoring documentation.
- Explore how Artifact Registry is used to store container images.
- Review the difference between GKE and Cloud Run.
- Open the Google Cloud Pricing Calculator and estimate a small deployment.

### Cloudflare

- Explore DNS records, CDN, caching, SSL/TLS and WAF.
- Review how Cloudflare can sit in front of an application hosted on another cloud.
- Read the Workers, Pages and R2 documentation.
- Review the pricing and plan limits for the services being explored.

## 10. Conclusion

AWS, Microsoft Azure and Google Cloud Platform provide a wide range of services for building, deploying and managing applications. Their core capabilities include compute, storage, databases, networking, security, containers and monitoring.

Cloudflare provides complementary services that help improve application performance, manage DNS, protect internet-facing applications and run code at the edge.

From a DevOps perspective, understanding these platforms helps engineers select suitable services, automate deployments, manage infrastructure, secure applications, monitor workloads and control cloud costs.

The most important learning outcome is understanding the purpose of each service and how services work together to support a real application—not simply memorizing product names.

---

## 11. Official Documentation and Learning Links

| Platform | Documentation | Learning resource | Pricing |
|---|---|---|---|
| AWS | [AWS Docs](https://docs.aws.amazon.com/) | [AWS Skill Builder](https://skillbuilder.aws/) | [AWS Pricing Calculator](https://calculator.aws/) |
| Azure | [Azure Docs](https://learn.microsoft.com/azure/) | [Microsoft Learn](https://learn.microsoft.com/training/azure/) | [Azure Pricing Calculator](https://azure.microsoft.com/pricing/calculator/) |
| GCP | [Google Cloud Docs](https://cloud.google.com/docs) | [Google Cloud Skills Boost](https://www.cloudskillsboost.google/) | [Google Cloud Pricing Calculator](https://cloud.google.com/products/calculator) |
| Cloudflare | [Cloudflare Developers](https://developers.cloudflare.com/) | [Cloudflare Learning Center](https://www.cloudflare.com/learning/) | [Cloudflare Plans](https://www.cloudflare.com/plans/) |

**Pricing note:** Cloud pricing changes and depends on region, configuration, usage and account eligibility. The pricing section describes the main billing factors rather than fixed monthly estimates. Always check the official pricing pages and calculators for current rates.

---
