# Task 4: Cloud Platform Exploration
 
Platforms covered: AWS, Microsoft Azure, Google Cloud Platform (GCP), Cloudflare
 
Author: Lakshmiprabha G
 
## 1. Scope and Approach
 
This document summarises what I learned by reading the official documentation and learning resources of the four platforms. It is an exploration task: no paid cloud resources were created and no purchases were made. Service descriptions reflect the official documentation. Free tier terms, limits and prices change often, so always confirm them on each provider's pricing page before using anything.
 
## 2. Amazon Web Services (AWS)
 
### Overview
 
AWS is the largest and oldest of the general-purpose cloud providers, with the broadest service catalogue. Resources live in Regions, each made of multiple Availability Zones. Most services can be managed through the web console, CLI, SDKs or Infrastructure as Code (CloudFormation, Terraform, CDK).
 
### Important services and their purpose
 
- **Compute - EC2:** virtual machines with full control over OS and networking. Used for traditional apps, custom workloads and self-managed software.
- **Compute - Lambda:** serverless functions that run on events (API calls, file uploads, schedules) and bill per execution.
- **Containers - ECS, EKS, ECR, Fargate:** ECS is AWS's own container orchestrator, EKS is managed Kubernetes, ECR is the container image registry, and Fargate runs containers without managing servers.
- **Storage - S3:** object storage for files, backups, static websites and data lakes. EBS provides block storage for EC2 and EFS provides shared file storage.
- **Networking - VPC, Route 53, CloudFront, ELB:** VPC is the private network (subnets, route tables, security groups), Route 53 is DNS, CloudFront is the CDN, and Elastic Load Balancing distributes traffic across targets.
- **Databases - RDS, Aurora, DynamoDB:** RDS is managed relational databases, Aurora is AWS's high-performance relational engine, and DynamoDB is a managed NoSQL key-value store.
- **Security and identity - IAM, KMS, Secrets Manager:** IAM controls who can do what through users, roles and policies. KMS manages encryption keys. Secrets Manager stores credentials and rotates them.
- **Monitoring - CloudWatch, CloudTrail:** CloudWatch collects metrics, logs and alarms. CloudTrail records API activity for auditing.
- **DevOps tooling - CloudFormation, CodePipeline, CodeBuild:** CloudFormation provisions infrastructure from templates. CodePipeline and CodeBuild provide CI/CD.
### Documentation and learning resources
 
- Official documentation: https://docs.aws.amazon.com
- AWS Skill Builder: https://skillbuilder.aws (courses, labs and exam preparation)
- AWS Well-Architected Framework: best-practice guidance across security, reliability, cost, performance, operations and sustainability
- AWS Free Tier page: lists what is free and under which conditions
## 3. Microsoft Azure
 
### Overview
 
Azure is Microsoft's cloud platform, strongest in enterprises that already use Microsoft products such as Windows Server, Microsoft 365 and Active Directory. Resources are organised in a hierarchy of Management Groups, Subscriptions, Resource Groups and Resources, and can be deployed through the portal, CLI, PowerShell, ARM/Bicep templates or Terraform.
 
### Important services and their purpose
 
- **Compute - Virtual Machines:** Windows or Linux VMs with full control. Virtual Machine Scale Sets handle auto scaling.
- **App hosting - App Service, Azure Functions:** App Service hosts web apps and APIs without managing servers. Functions is serverless, event-driven code.
- **Containers - AKS, Container Apps, ACR:** AKS is managed Kubernetes, Container Apps runs containers serverlessly, and Azure Container Registry stores images.
- **Storage - Blob Storage, Azure Files, Managed Disks:** Blob is object storage, Files is managed file shares, and Managed Disks back virtual machines.
- **Networking - Virtual Network, Load Balancer, Application Gateway, Front Door, Azure DNS:** VNet is the private network, Load Balancer and Application Gateway distribute traffic (layer 4 and layer 7), Front Door is a global entry point with CDN features, and Azure DNS hosts DNS zones.
- **Databases - Azure SQL, Cosmos DB, Azure Database for PostgreSQL/MySQL:** managed relational databases, plus Cosmos DB as a globally distributed NoSQL database.
- **Identity and security - Microsoft Entra ID, RBAC, Key Vault, Defender for Cloud:** Entra ID (formerly Azure Active Directory) is the identity service. RBAC controls access to resources. Key Vault stores secrets, keys and certificates. Defender for Cloud provides security posture management.
- **Monitoring - Azure Monitor, Log Analytics, Application Insights:** metrics, logs and application performance monitoring.
- **DevOps tooling - Azure DevOps, ARM/Bicep:** Azure DevOps offers repos, pipelines, boards and artifacts. Bicep and ARM templates provide Infrastructure as Code.
### Documentation and learning resources
 
- Official documentation: https://learn.microsoft.com/azure
- Microsoft Learn: free learning paths, modules and sandboxes aligned to Azure certifications (for example AZ-900 Azure Fundamentals)
- Azure Architecture Center: reference architectures and design guidance
- Azure free account page: describes what is free and what needs a paid upgrade
## 4. Google Cloud Platform (GCP)
 
### Overview
 
GCP is Google's cloud, known for strong data analytics, machine learning and Kubernetes (Google created Kubernetes). Resources are organised into Organization, Folders and Projects, and a Project is the main unit for billing, APIs and access control. Management is available through the console, the gcloud CLI, client libraries and Terraform.
 
### Important services and their purpose
 
- **Compute - Compute Engine:** virtual machines with custom machine types and managed instance groups for scaling.
- **Serverless - Cloud Run, Cloud Functions, App Engine:** Cloud Run runs any container serverlessly and is one of the simplest ways to deploy a containerised service. Cloud Functions runs event-driven code. App Engine is a managed application platform.
- **Containers - GKE, Artifact Registry:** GKE is managed Kubernetes and Artifact Registry stores container images and packages.
- **Storage - Cloud Storage, Persistent Disk, Filestore:** Cloud Storage is object storage, Persistent Disk is block storage, and Filestore is managed NFS.
- **Networking - VPC, Cloud Load Balancing, Cloud CDN, Cloud DNS:** VPC networks in GCP are global, load balancing supports global anycast front ends, and Cloud CDN and Cloud DNS cover delivery and DNS.
- **Databases and analytics - Cloud SQL, Spanner, Firestore, BigQuery:** Cloud SQL is managed MySQL/PostgreSQL/SQL Server, Spanner is a globally consistent relational database, Firestore is a NoSQL document database, and BigQuery is a serverless data warehouse for large-scale analytics.
- **Identity and security - IAM, Secret Manager, Cloud KMS:** IAM grants roles to identities on resources, Secret Manager stores secrets, and Cloud KMS manages encryption keys.
- **Operations - Cloud Logging, Cloud Monitoring:** centralised logs, metrics, dashboards and alerts.
- **DevOps tooling - Cloud Build, Cloud Deploy:** Cloud Build runs CI builds and Cloud Deploy handles delivery pipelines.
### Documentation and learning resources
 
- Official documentation: https://cloud.google.com/docs
- Google Cloud Skills Boost: https://www.cloudskillsboost.google (hands-on labs and learning paths)
- Google Cloud Architecture Center: reference architectures and best practices
- Free tier and free trial pages: describe current always-free usage limits and trial credit terms
## 5. Cloudflare
 
### Overview
 
Cloudflare is different from the other three. It started as a CDN, DNS and security provider that sits in front of websites, and it has grown into an edge platform that runs code and stores data across its global network. It is usually used alongside AWS, Azure or GCP rather than as a full replacement for them, although some applications can be built entirely on Cloudflare.
 
### Important services and their purpose
 
- **DNS:** authoritative DNS hosting, usually the entry point for adding a domain to Cloudflare.
- **CDN and caching:** caches content at edge locations close to users to improve speed and reduce load on the origin server.
- **Security - WAF, DDoS protection, Bot management, Rate limiting:** filters malicious traffic before it reaches the origin. DDoS mitigation is part of the core platform.
- **SSL/TLS:** manages certificates and encryption modes between visitor, Cloudflare and origin.
- **Workers:** serverless code that runs at the edge on Cloudflare's network, used for APIs, request routing and edge logic.
- **Pages:** hosting for static sites and full-stack frontends with Git-based deployments.
- **Storage and data - R2, KV, D1, Durable Objects:** R2 is S3-compatible object storage, KV is a global key-value store, D1 is a serverless SQL database, and Durable Objects provide stateful coordination at the edge.
- **Tunnel:** exposes internal services to the internet through an outbound connection, without opening inbound firewall ports.
- **Zero Trust - Access, Gateway:** identity-aware access to applications and secure web gateway features, as an alternative to a traditional VPN.
- **Load Balancing:** traffic distribution and health-check-based failover across origins.
### Documentation and learning resources
 
- Official documentation: https://developers.cloudflare.com
- Cloudflare Learning Center: https://www.cloudflare.com/learning (beginner-friendly explanations of DNS, CDN, DDoS, TLS and related topics)
- Workers and Pages documentation with tutorials and examples
- Cloudflare plans page: describes what is available on the Free plan versus paid plans
## 6. Comparison of Equivalent Services
 
- **Virtual machines:** AWS EC2, Azure Virtual Machines, GCP Compute Engine. Cloudflare has no equivalent.
- **Serverless functions:** AWS Lambda, Azure Functions, GCP Cloud Functions, Cloudflare Workers (runs at the edge).
- **Serverless containers:** AWS Fargate (with ECS/EKS), Azure Container Apps, GCP Cloud Run. Cloudflare has no direct equivalent.
- **Managed Kubernetes:** AWS EKS, Azure AKS, GCP GKE.
- **Container registry:** AWS ECR, Azure Container Registry, GCP Artifact Registry.
- **Object storage:** AWS S3, Azure Blob Storage, GCP Cloud Storage, Cloudflare R2.
- **Managed relational database:** AWS RDS/Aurora, Azure SQL Database, GCP Cloud SQL, Cloudflare D1 (lightweight, SQLite-based).
- **NoSQL:** AWS DynamoDB, Azure Cosmos DB, GCP Firestore, Cloudflare KV.
- **DNS:** AWS Route 53, Azure DNS, GCP Cloud DNS, Cloudflare DNS.
- **CDN:** AWS CloudFront, Azure Front Door/CDN, GCP Cloud CDN, Cloudflare CDN.
- **Identity and access:** AWS IAM, Microsoft Entra ID with Azure RBAC, GCP IAM, Cloudflare Access (for application access).
- **Secrets:** AWS Secrets Manager, Azure Key Vault, GCP Secret Manager.
- **Monitoring and logging:** AWS CloudWatch, Azure Monitor, GCP Cloud Monitoring and Logging.
- **CI/CD:** AWS CodePipeline/CodeBuild, Azure DevOps/Pipelines, GCP Cloud Build/Cloud Deploy. Cloudflare Pages and Workers have built-in Git-based deployment.
## 7. Key Takeaways
 
- AWS has the widest service range and the largest ecosystem. Its breadth also means more services to learn and more configuration decisions.
- Azure fits best where an organisation already depends on Microsoft identity and tooling (Entra ID, Microsoft 365, Windows workloads).
- GCP is strongest for data analytics (BigQuery), Kubernetes (GKE) and simple container deployment (Cloud Run).
- Cloudflare is mainly an edge, networking and security layer, with a growing developer platform. It complements the other three.
- The core concepts are the same across all four: compute, storage, networking, identity and access, monitoring, and Infrastructure as Code. Knowing them on one platform makes learning another much faster.
- Every provider uses a shared responsibility model: the provider secures the underlying infrastructure and the customer secures configuration, identities and data.
- Cost control matters on every platform. Set budgets and alerts, and delete unused resources.
## 8. References
 
- AWS: https://docs.aws.amazon.com, https://skillbuilder.aws
- Azure: https://learn.microsoft.com/azure
- GCP: https://cloud.google.com/docs, https://www.cloudskillsboost.google
- Cloudflare: https://developers.cloudflare.com, https://www.cloudflare.com/learning