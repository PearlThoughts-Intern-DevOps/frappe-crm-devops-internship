# Task 4: Cloud Platform Exploration

**Author:** Harsh Saini
**Platforms covered:** AWS, Microsoft Azure, Google Cloud Platform (GCP), Cloudflare

> **Scope note:** This is an exploration task. No paid cloud resources were created and no purchases were made. AWS was viewed through the console in read-only mode. Azure, GCP and Cloudflare were explored through their official documentation, product pages and free learning platforms. Pricing, free-tier limits and service names change often, so check the linked official pages for current numbers.

## Table of contents

1. Cloud computing fundamentals
2. Amazon Web Services (AWS)
3. Microsoft Azure
4. Google Cloud Platform (GCP)
5. Cloudflare
6. Comparison of the four platforms
7. How these platforms are used in DevOps
8. Summary and my findings

---

## 1. Cloud computing fundamentals

Cloud computing means renting computing resources (servers, storage, databases, networking, analytics, AI) over the internet and paying only for what is used, instead of buying and maintaining physical hardware. Before looking at individual platforms, these are the ideas that apply to all of them.

### 1.1 Service models

| Model | What the customer manages | What the provider manages | Examples |
|---|---|---|---|
| **IaaS** (Infrastructure as a Service) | OS, runtime, application, data | Physical hardware, virtualization, base network | EC2, Azure Virtual Machines, Compute Engine |
| **PaaS** (Platform as a Service) | Application code and data | Servers, OS, runtime, scaling | Elastic Beanstalk, Azure App Service, App Engine |
| **FaaS / Serverless** | Only function code | Everything else, including scaling to zero | Lambda, Azure Functions, Cloud Functions, Cloudflare Workers |
| **SaaS** (Software as a Service) | Just uses the software | Everything | Gmail, Microsoft 365, Salesforce |

### 1.2 Deployment models
- **Public cloud:** resources run on the provider's shared infrastructure (all four platforms here).
- **Private cloud:** infrastructure dedicated to one organization.
- **Hybrid cloud:** on-premises plus public cloud working together (Azure Arc, AWS Outposts, Google Distributed Cloud).
- **Multi-cloud:** using more than one provider, for example workloads on AWS with Cloudflare in front.

### 1.3 Core concepts shared by every provider
- **Region:** a geographic area containing multiple data centers (for example Mumbai).
- **Availability Zone (AZ):** one or more isolated data centers inside a region. Spreading an app across AZs gives high availability.
- **Edge location / Point of Presence (PoP):** small sites close to users, used for caching and low-latency delivery.
- **Shared responsibility model:** the provider secures the cloud itself (hardware, facilities, core services); the customer secures what they put in it (data, identities, configuration, application code).
- **IAM (Identity and Access Management):** controls who can do what on which resource. The guiding rule is least privilege.
- **Elasticity and scalability:** resources grow and shrink with demand (vertical scaling = bigger machine, horizontal scaling = more machines).
- **High availability and fault tolerance:** designing so that a single failure does not take the system down.
- **Pricing models:** pay-as-you-go (On-Demand), commitment discounts (Reserved Instances / Savings Plans / Committed Use), and deeply discounted interruptible capacity (Spot / Preemptible).
- **Infrastructure as Code (IaC):** defining infrastructure in files (Terraform, CloudFormation, Bicep) so it is repeatable and version-controlled.
- **Ways to interact:** web console, command-line interface (CLI), SDKs, and REST APIs.

---

## 2. Amazon Web Services (AWS)

### 2.1 Overview
AWS launched in 2006 and is the oldest and largest cloud provider. It has the broadest catalog of services (well over 200), the largest community and the most third-party tooling, tutorials and job demand. It originally grew out of Amazon's own need to run its retail infrastructure at scale.

- **Console:** https://console.aws.amazon.com
- **Documentation:** https://docs.aws.amazon.com
- **Tools to interact:** Management Console, AWS CLI, SDKs (Python/boto3, JavaScript, Java and others), CloudShell (browser-based terminal)

### 2.2 Global infrastructure
- **Regions:** independent geographic areas (for example us-east-1 in N. Virginia, ap-south-1 in Mumbai). Each region is isolated from the others.
- **Availability Zones:** each region has multiple AZs (for example ap-south-1a, 1b, 1c) that are physically separate but connected by low-latency links.
- **Edge locations:** used by CloudFront and Route 53 for content delivery and DNS close to users.
- **Local Zones / Wavelength / Outposts:** extend AWS closer to specific cities, 5G networks, or into on-premises data centers.

### 2.3 Account structure, identity and security model
- **AWS Account:** the basic container for resources and billing.
- **AWS Organizations:** manage many accounts together, with consolidated billing and **Service Control Policies (SCPs)** that set guardrails.
- **IAM:** users, groups, **roles** (temporary credentials assumed by people or services) and **policies** (JSON documents defining allowed or denied actions).
- **Best practices:** enable MFA on the root user, never use the root account for daily work, give each workload an IAM role instead of long-lived access keys, and apply least privilege.
- **Related security services:** KMS (encryption keys), Secrets Manager, Security Groups and NACLs (network firewalls), WAF, Shield (DDoS), GuardDuty (threat detection), Inspector, Security Hub, CloudTrail (audit logging).

### 2.4 Important services in depth

#### Compute
- **EC2 (Elastic Compute Cloud):** resizable virtual machines. You pick an instance type by family: general purpose (T, M), compute optimized (C), memory optimized (R, X), storage optimized (I, D), accelerated/GPU (P, G). Billing options are On-Demand, Savings Plans / Reserved Instances (commit for 1 or 3 years for a discount) and Spot (spare capacity at a large discount but can be reclaimed). Used for web servers, application servers, CI runners and legacy apps. Includes Auto Scaling groups to add and remove instances automatically.
- **AWS Lambda:** run code in response to events (an API call, an S3 upload, a schedule) without managing servers. You pay per request and per millisecond of execution, and functions have a maximum run time of 15 minutes. Used for APIs (with API Gateway), file processing, scheduled jobs and glue logic between services.
- **Containers (ECS, EKS, Fargate, ECR):** ECS is AWS's own container orchestrator; EKS is managed Kubernetes; Fargate runs containers without managing the underlying servers; ECR is a private Docker image registry.
- **Elastic Beanstalk and Lightsail:** Beanstalk is a simple PaaS (upload code, AWS handles deployment); Lightsail is a beginner-friendly VPS with fixed monthly pricing.
- **Batch, App Runner, Outposts:** batch job scheduling, simple container web app hosting, and AWS hardware in your own data center.

#### Storage
- **S3 (Simple Storage Service):** virtually unlimited object storage accessed over HTTP. Data is stored in **buckets** as **objects**. Storage classes trade cost for access speed: Standard, Intelligent-Tiering, Standard-IA, One Zone-IA, and the Glacier family (Instant, Flexible, Deep Archive) for archives. Supports versioning, lifecycle rules, encryption and static website hosting. Used for backups, media, logs, data lakes and website assets.
- **EBS (Elastic Block Store):** network-attached disks for EC2, with snapshots for backup.
- **EFS and FSx:** managed shared file systems (NFS, Windows, Lustre).
- **AWS Backup, Storage Gateway, Snow family:** centralized backups, hybrid storage, and physical data transfer devices.

#### Databases
- **RDS (Relational Database Service):** managed MySQL, PostgreSQL, MariaDB, Oracle and SQL Server with automated backups, patching, Multi-AZ failover and read replicas.
- **Aurora:** AWS's cloud-native MySQL- and PostgreSQL-compatible database, designed for higher performance and availability than standard RDS.
- **DynamoDB:** fully managed serverless NoSQL key-value and document database with single-digit-millisecond latency at any scale.
- **ElastiCache:** managed Redis and Memcached for caching and session storage.
- **Others:** Redshift (data warehouse), DocumentDB (MongoDB-compatible), Neptune (graph), Timestream (time series).

#### Networking and content delivery
- **VPC (Virtual Private Cloud):** your own isolated virtual network with subnets (public and private), route tables, an Internet Gateway, NAT Gateway, Security Groups (stateful firewalls on instances) and Network ACLs (stateless firewalls on subnets). Almost everything else in AWS sits inside a VPC.
- **Route 53:** scalable DNS, domain registration, health checks and traffic routing policies.
- **CloudFront:** CDN that caches content at edge locations.
- **Elastic Load Balancing:** Application Load Balancer (Layer 7, HTTP/HTTPS routing), Network Load Balancer (Layer 4, very high performance), Gateway Load Balancer.
- **API Gateway, Direct Connect, VPN, Transit Gateway:** managed API front door, dedicated private connection to AWS, secure links, and hub-and-spoke network connectivity.

#### Management, monitoring and DevOps
- **CloudWatch:** metrics, logs, alarms and dashboards. CloudWatch Logs collects application logs; alarms can trigger scaling or notifications.
- **CloudTrail:** records API activity in your account for auditing and security investigations.
- **CloudFormation:** AWS-native Infrastructure as Code using YAML/JSON templates. **AWS CDK** lets you define the same infrastructure in programming languages.
- **Systems Manager, Config, Trusted Advisor:** operations tooling, configuration compliance tracking and best-practice checks.
- **CodeCommit, CodeBuild, CodeDeploy, CodePipeline:** AWS's CI/CD services (many teams use GitHub Actions or Jenkins instead).

#### Messaging and integration
- **SQS:** message queues for decoupling components. **SNS:** publish/subscribe notifications. **EventBridge:** event bus connecting AWS services and SaaS apps. **Step Functions:** workflow orchestration.

#### Analytics, AI and ML
- **Athena, Glue, EMR, Kinesis, QuickSight:** query data in S3 with SQL, ETL and data catalog, big data processing, streaming ingestion, BI dashboards.
- **SageMaker:** build, train and deploy machine learning models. **Bedrock:** API access to foundation models. **Rekognition, Comprehend, Textract, Polly, Transcribe:** ready-made AI services for images, text, documents and speech.

#### Cost management
- **Billing console, Cost Explorer, Budgets, Cost and Usage Reports:** view and forecast spend and set alerts. Tags on resources let you attribute cost to teams or projects.

### 2.5 Example architecture: a typical three-tier web application
1. Users resolve the domain through **Route 53**.
2. **CloudFront** serves cached static content and **WAF** filters malicious traffic.
3. An **Application Load Balancer** distributes requests across **EC2 instances (or ECS/Fargate containers)** in private subnets of a **VPC**, spread across two AZs, managed by an Auto Scaling group.
4. The application stores data in **RDS/Aurora** (Multi-AZ) and uploads files to **S3**.
5. **CloudWatch** collects logs and metrics, **CloudTrail** audits changes, and **IAM roles** give the app permission to reach S3 without hard-coded keys.

### 2.6 Pricing model and free usage
- Most services are **pay-as-you-go**: per hour or second for compute, per GB-month for storage, per request or per GB transferred for networking.
- **Data transfer out** to the internet is charged; traffic into AWS is generally free.
- Discounts come from Savings Plans, Reserved Instances and Spot.
- AWS offers a **Free Tier / free plan** for new accounts with limited usage allowances or credits. The rules have changed over time, so read the current terms at https://aws.amazon.com/free/.
- Use the **AWS Pricing Calculator** (https://calculator.aws) to estimate cost without creating anything.

### 2.7 Official documentation and learning resources
- Documentation: https://docs.aws.amazon.com (each service has a User Guide, API Reference and CLI reference)
- AWS Skill Builder (free and paid courses, labs): https://skillbuilder.aws
- AWS Cloud Practitioner Essentials course and certification: https://aws.amazon.com/certification/certified-cloud-practitioner/
- Certification path: Cloud Practitioner, then Associate level (Solutions Architect, Developer, SysOps/CloudOps), then Professional and Specialty.
- AWS Well-Architected Framework (six pillars: operational excellence, security, reliability, performance efficiency, cost optimization, sustainability): https://aws.amazon.com/architecture/well-architected/
- Architecture Center and reference diagrams: https://aws.amazon.com/architecture/
- AWS Workshops: https://workshops.aws
- Free Tier: https://aws.amazon.com/free/

### 2.8 Strengths and limitations
**Strengths:** widest service catalog, most mature, largest community and documentation, strong global footprint, huge job market.
**Limitations:** the sheer number of services is overwhelming for beginners, pricing is complex, and data egress costs can add up.

### 2.9 What I explored hands-on
Viewed the AWS Management Console in read-only mode: the services menu and how services are grouped, the Billing and Free Tier pages, and the region selector. No resources were created.

---

## 3. Microsoft Azure

### 3.1 Overview
Azure launched in 2010 and is the second-largest cloud provider. Its major advantage is deep integration with the Microsoft ecosystem: Windows Server, SQL Server, Active Directory (now Microsoft Entra ID), Microsoft 365, Visual Studio, .NET and GitHub. It is the natural choice for many enterprises already invested in Microsoft products, and it has a strong hybrid cloud story.

- **Portal:** https://portal.azure.com
- **Documentation:** https://learn.microsoft.com/azure
- **Tools to interact:** Azure Portal, Azure CLI (`az`), Azure PowerShell, Cloud Shell, SDKs, Visual Studio / VS Code extensions

### 3.2 Global infrastructure
- **Regions:** a very large number of regions worldwide, including several in India.
- **Availability Zones:** many regions have three physically separate zones for zone-redundant services.
- **Region pairs:** each region is paired with another in the same geography for disaster recovery and staged updates.
- **Azure Edge Zones, Azure Arc, Azure Stack:** extend Azure services to edge locations and on-premises or other clouds, supporting hybrid scenarios.

### 3.3 Account structure, identity and security model
Azure organizes resources in a hierarchy:

**Tenant (Microsoft Entra ID) > Management Groups > Subscriptions > Resource Groups > Resources**

- **Subscription:** a billing and access boundary.
- **Resource Group:** a logical container for related resources that share a lifecycle (you can delete a whole group at once).
- **Microsoft Entra ID:** the identity provider for users, groups, apps and service principals; supports SSO, MFA and Conditional Access.
- **Azure RBAC (role-based access control):** assigns roles such as Owner, Contributor and Reader at any scope (subscription, resource group or resource).
- **Managed Identities:** let Azure resources authenticate to other services without stored credentials.
- **Security services:** Key Vault (secrets, keys, certificates), Microsoft Defender for Cloud, Network Security Groups (NSGs), Azure Firewall, Azure DDoS Protection, Azure Policy for compliance rules.

### 3.4 Important services in depth

#### Compute
- **Virtual Machines:** IaaS VMs in many series (general purpose, compute, memory, storage, GPU). Supports Linux and Windows. **Virtual Machine Scale Sets** auto-scale groups of identical VMs. Cost savers: Reserved Instances, Spot VMs, and **Azure Hybrid Benefit** (reuse existing Windows Server/SQL Server licenses).
- **App Service:** PaaS for hosting web apps, REST APIs and mobile backends in .NET, Java, Node.js, Python and PHP, with built-in autoscaling, deployment slots (for blue/green deployment), custom domains and TLS.
- **Azure Functions:** serverless, event-driven code with triggers (HTTP, timers, queues, blobs). Offered in several hosting plans, including a consumption-style pay-per-execution plan.
- **Containers:** **AKS** (managed Kubernetes), **Azure Container Apps** (serverless containers built on Kubernetes, suited to microservices), **Azure Container Instances** (run a single container quickly), **Azure Container Registry** (private image registry).
- **Others:** Azure Batch, Azure Virtual Desktop, Azure Static Web Apps.

#### Storage
- **Storage Account:** the umbrella that provides several storage services:
  - **Blob Storage:** object storage with access tiers Hot, Cool, Cold and Archive.
  - **Azure Files:** managed SMB/NFS file shares.
  - **Queue Storage and Table Storage:** simple queues and key-attribute store.
- **Managed Disks:** block storage for VMs.
- **Redundancy options:** LRS (three copies in one datacenter), ZRS (across zones), GRS (copied to a paired region), GZRS.

#### Databases
- **Azure SQL Database / SQL Managed Instance:** managed Microsoft SQL Server engine.
- **Azure Database for PostgreSQL and MySQL:** managed open-source databases.
- **Cosmos DB:** globally distributed, multi-model NoSQL database with low latency and multiple APIs (NoSQL, MongoDB, Cassandra, Gremlin, Table).
- **Azure Cache for Redis:** managed Redis.
- **Synapse Analytics / Microsoft Fabric:** analytics and data warehousing platforms.

#### Networking
- **Virtual Network (VNet):** private network with subnets, peering and VPN connectivity.
- **Load balancing options:** Azure Load Balancer (Layer 4), Application Gateway (Layer 7 with WAF), Traffic Manager (DNS-based), and **Azure Front Door** (global entry point with CDN, WAF and acceleration).
- **Azure DNS, Azure CDN, VPN Gateway, ExpressRoute:** DNS hosting, content delivery, site-to-site VPN, and a dedicated private connection to Azure.
- **Private Link and Bastion:** private access to PaaS services and secure RDP/SSH without public IPs.

#### Identity and access
- **Microsoft Entra ID** (formerly Azure Active Directory), **Entra External ID** for customer identities, **Privileged Identity Management** for just-in-time admin access.

#### Monitoring and management
- **Azure Monitor:** collects metrics and logs; **Log Analytics** queries logs with KQL (Kusto Query Language); **Application Insights** provides application performance monitoring.
- **Azure Policy, Blueprints/Landing zones, Advisor, Cost Management + Billing:** governance, recommendations on cost, security and reliability, and spend tracking with budgets.

#### DevOps and Infrastructure as Code
- **Azure DevOps** (Repos, Boards, Pipelines, Artifacts, Test Plans) and **GitHub Actions** (Microsoft owns GitHub) for CI/CD.
- **ARM templates and Bicep** (Azure-native IaC; Bicep is a cleaner language that compiles to ARM), plus Terraform.

#### Messaging and integration
- **Service Bus** (enterprise queues/topics), **Event Grid** (event routing), **Event Hubs** (high-volume streaming ingestion), **Logic Apps** (low-code workflow automation), **API Management**.

#### AI and ML
- **Azure AI Foundry / Azure OpenAI Service:** access to OpenAI and other foundation models. **Azure Machine Learning:** model training and MLOps. **Azure AI Services:** vision, speech, language and document intelligence APIs.

### 3.5 Example architecture: a web application on Azure
1. **Azure Front Door** with WAF receives traffic globally.
2. It routes to **App Service** (or **AKS / Container Apps**) in a **VNet**.
3. The app reads and writes data in **Azure SQL Database** or **Cosmos DB** and stores files in **Blob Storage**.
4. Secrets are held in **Key Vault**, accessed through a **Managed Identity**.
5. Users sign in through **Microsoft Entra ID**.
6. **Azure Monitor and Application Insights** provide logs, metrics and alerts; **Azure Pipelines or GitHub Actions** deploy the code.

### 3.6 Pricing model and free usage
- Pay-as-you-go, with Reserved Instances, Savings Plans and Spot pricing for discounts, plus Azure Hybrid Benefit for existing Microsoft licenses.
- The **Azure free account** has historically included a limited-time starting credit, a set of services free for the first 12 months, and a list of services that are always free within limits. Check the current terms at https://azure.microsoft.com/free/ because they change.
- The **Azure Pricing Calculator** (https://azure.microsoft.com/pricing/calculator/) estimates cost without creating resources.
- Students can often get free credits through the Azure for Students offer, which usually does not require a credit card (verify eligibility).

### 3.7 Official documentation and learning resources
- Documentation: https://learn.microsoft.com/azure
- Microsoft Learn (free, interactive learning paths and sandbox modules): https://learn.microsoft.com/training/azure/
- Certifications: **AZ-900 Azure Fundamentals** (beginner), then AZ-104 Administrator, AZ-204 Developer, AZ-305 Solutions Architect, AZ-400 DevOps Engineer.
- Azure Architecture Center (reference architectures and design patterns): https://learn.microsoft.com/azure/architecture/
- Cloud Adoption Framework and Well-Architected Framework: https://learn.microsoft.com/azure/well-architected/
- Azure Free Account: https://azure.microsoft.com/free/

### 3.8 Strengths and limitations
**Strengths:** best fit for Microsoft-centric enterprises, strong hybrid cloud (Arc, Stack), excellent identity platform (Entra ID), good developer tooling with .NET and Visual Studio, strong enterprise support and compliance coverage.
**Limitations:** the portal and service naming can feel sprawling and has changed over the years (for example Azure AD renamed to Entra ID), and some services have overlapping options that make choosing harder.

### 3.9 What I explored
Reviewed the product catalog and documentation: how the subscription/resource group hierarchy works, the main service categories, the Microsoft Learn AZ-900 learning path and the Architecture Center. No account was created.

---

## 4. Google Cloud Platform (GCP)

### 4.1 Overview
GCP launched publicly in 2008 (App Engine) and grew into a full cloud platform. It runs on the same global infrastructure that powers Google Search, YouTube and Gmail. Google is known for inventing technologies that became industry standards: **Kubernetes** (from internal system Borg), **TensorFlow**, MapReduce/Bigtable concepts, and **BigQuery**. GCP is especially strong in data analytics, machine learning, containers and global networking.

- **Console:** https://console.cloud.google.com
- **Documentation:** https://cloud.google.com/docs
- **Tools to interact:** Cloud Console, `gcloud` CLI, Cloud Shell (browser terminal with a free persistent home directory), client libraries, Terraform

### 4.2 Global infrastructure
- **Regions and zones:** regions such as asia-south1 (Mumbai) contain multiple zones (for example asia-south1-a).
- **Premium Tier network:** traffic travels on Google's private global fiber backbone for as long as possible, which improves latency and reliability.
- **Global VPC:** a single VPC network spans all regions, unlike providers where VPCs are regional.
- **Edge:** Cloud CDN and global load balancing use Google's worldwide edge points of presence.

### 4.3 Resource hierarchy, identity and security model
**Organization > Folders > Projects > Resources**

- **Project:** the core unit. It owns resources, links to a billing account and has its own set of enabled APIs and permissions. Many services require you to enable their API in a project first.
- **IAM:** you grant **roles** to **principals** (users, groups, service accounts) on a resource. Role types are Basic (Owner, Editor, Viewer; very broad), Predefined (fine-grained, per service) and Custom.
- **Service accounts:** identities for applications and workloads. Prefer attached service accounts or Workload Identity over downloaded key files.
- **Security services:** Secret Manager, Cloud KMS, VPC firewall rules, Cloud Armor (WAF and DDoS), Security Command Center, VPC Service Controls (data exfiltration perimeters), Identity-Aware Proxy.

### 4.4 Important services in depth

#### Compute
- **Compute Engine:** virtual machines with predefined or custom machine types. Billing is per second. Discounts include **sustained use discounts** (applied automatically for long-running usage on eligible machines), **committed use discounts** and **Spot VMs**. Supports live migration of VMs during maintenance.
- **Cloud Run:** run any container as a fully managed serverless service. It scales automatically, including down to zero, and you pay for actual request time. Often the easiest way to deploy a web app or API on GCP.
- **Cloud Functions (Cloud Run functions):** event-driven functions for small pieces of code.
- **GKE (Google Kubernetes Engine):** managed Kubernetes, considered among the most mature offerings. **Autopilot mode** manages nodes for you; **Standard mode** gives more control.
- **App Engine:** one of the earliest PaaS offerings for web apps, with standard and flexible environments.
- **Others:** Batch, Bare Metal Solution, VMware Engine.

#### Storage
- **Cloud Storage:** object storage in buckets with classes **Standard, Nearline, Coldline and Archive**, plus lifecycle management and location options (regional, dual-region, multi-region). Used for backups, media, data lakes and static assets.
- **Persistent Disk / Hyperdisk:** block storage for VMs. **Filestore:** managed NFS file storage.
- **Backup and DR, Storage Transfer Service:** protection and bulk data movement.

#### Databases
- **Cloud SQL:** managed MySQL, PostgreSQL and SQL Server. **AlloyDB:** high-performance PostgreSQL-compatible database.
- **Cloud Spanner:** horizontally scalable relational database with strong global consistency, a standout service for global applications.
- **Firestore:** serverless document NoSQL database with real-time sync (popular for mobile and web apps). **Bigtable:** wide-column NoSQL for very large, low-latency workloads.
- **Memorystore:** managed Redis, Valkey and Memcached.

#### Data and analytics
- **BigQuery:** serverless data warehouse. You load or query huge datasets with standard SQL and pay for data scanned (on-demand) or reserved capacity, with no clusters to manage. One of GCP's flagship services.
- **Pub/Sub:** global messaging and event ingestion. **Dataflow:** stream and batch data processing (Apache Beam). **Dataproc:** managed Spark and Hadoop. **Looker:** BI platform. **Dataform, Composer (managed Airflow), Data Fusion:** data pipelines and orchestration.

#### Networking
- **VPC:** global virtual network with regional subnets and firewall rules.
- **Cloud Load Balancing:** a single global anycast IP can front backends in multiple regions, with HTTP(S), TCP/UDP and internal load balancers.
- **Cloud CDN, Cloud DNS, Cloud NAT, Cloud VPN, Cloud Interconnect, Cloud Armor.**

#### Operations and DevOps
- **Cloud Monitoring and Cloud Logging** (formerly Stackdriver), plus **Cloud Trace, Error Reporting and Profiler** for application observability.
- **Cloud Build** (CI), **Artifact Registry** (container and package registry), **Cloud Deploy** (continuous delivery), **Cloud Source Repositories**.
- **Infrastructure as Code:** Terraform is the primary tool; **Infrastructure Manager** and Deployment Manager are Google-native options.

#### AI and ML
- **Vertex AI:** unified platform for training, tuning and deploying models, including access to **Gemini** foundation models and Model Garden.
- **Pre-trained APIs:** Vision, Speech-to-Text, Text-to-Speech, Natural Language, Translation, Document AI. **TPUs** (Google's custom AI chips) are available for ML workloads.

### 4.5 Example architecture: a containerized app with analytics
1. A **global external HTTP(S) load balancer** (with **Cloud Armor** and **Cloud CDN**) receives traffic on one anycast IP.
2. Requests go to a **Cloud Run** service (or **GKE** cluster).
3. The app uses **Cloud SQL** or **Firestore** for data and **Cloud Storage** for files; credentials come from **Secret Manager** and a dedicated **service account**.
4. Events are published to **Pub/Sub**, processed by **Dataflow** and loaded into **BigQuery** for reporting in **Looker**.
5. **Cloud Logging/Monitoring** provide visibility; **Cloud Build and Artifact Registry** build and store container images.

### 4.6 Pricing model and free usage
- Per-second billing for many services, automatic sustained use discounts on eligible Compute Engine usage, committed use discounts and Spot VMs.
- New customers have typically received a **time-limited free trial credit**, and there is an **Always Free** tier with monthly usage limits on selected products. Exact amounts and conditions change, so check https://cloud.google.com/free.
- Most services require billing to be enabled on a project. Use **budgets and alerts** in Billing to avoid surprises.
- **Pricing Calculator:** https://cloud.google.com/products/calculator estimates costs without creating resources.

### 4.7 Official documentation and learning resources
- Documentation: https://cloud.google.com/docs (includes quickstarts, tutorials and how-to guides for each product)
- **Google Cloud Skills Boost** (hands-on labs, quests and learning paths): https://www.cloudskillsboost.google
- Certifications: **Cloud Digital Leader** (beginner), Associate Cloud Engineer, then Professional certifications (Cloud Architect, Cloud Developer, Cloud DevOps Engineer, Data Engineer and others).
- Architecture Center (reference architectures, design guides): https://cloud.google.com/architecture
- Google Cloud Well-Architected Framework: https://cloud.google.com/architecture/framework
- Google Cloud Free Program: https://cloud.google.com/free

### 4.8 Strengths and limitations
**Strengths:** leading data analytics and ML tooling (BigQuery, Vertex AI), excellent Kubernetes, strong global network, clean and consistent console and CLI, simple per-second pricing with automatic discounts.
**Limitations:** smaller market share and ecosystem than AWS and Azure, fewer niche or enterprise-legacy services, and a smaller job market in some regions.

### 4.9 What I explored
Reviewed the product catalog and docs: the Organization/Folder/Project hierarchy, the main categories of services, Cloud Skills Boost learning paths and the Architecture Center. No account was created.

---

## 5. Cloudflare

### 5.1 Overview
Cloudflare was founded in 2009 and began as a service that sits in front of websites to make them faster and safer (CDN, DNS and DDoS protection). It has since grown into a connectivity cloud and developer platform. Its defining feature is its **global anycast edge network** spread across hundreds of cities: traffic is handled by the data center closest to the user, and code can run there too. Unlike AWS, Azure and GCP, Cloudflare does not offer general-purpose virtual machines; its focus is networking, security, performance and edge computing.

- **Dashboard:** https://dash.cloudflare.com
- **Documentation:** https://developers.cloudflare.com
- **Tools to interact:** Dashboard, **Wrangler** CLI (for Workers, Pages, R2, D1 and more), REST API, Terraform provider, SDKs

### 5.2 How it works
- **Anycast network:** the same IP addresses are announced from every data center, so each user's request automatically reaches the nearest one.
- **Reverse proxy:** you change your domain's nameservers to Cloudflare. Records marked "Proxied" (the orange cloud) send traffic through Cloudflare, which can cache it, filter attacks, apply rules and then forward legitimate requests to your origin server (which may be on AWS, Azure, GCP or anywhere).
- **Edge compute:** Workers run your code in the same data centers, so no region choice is needed.

### 5.3 Account structure and plans
- An **account** contains **zones** (one per domain) and developer resources (Workers, R2 buckets, D1 databases and so on).
- Plans for websites: **Free, Pro, Business, Enterprise**. The Free plan includes DNS, CDN, universal SSL and baseline DDoS protection. Developer products (Workers, Pages, R2, D1, KV) have their own free allowances and optional paid plans.
- **Access control:** account members with roles, API tokens with scoped permissions, and Cloudflare Access for application-level access.

### 5.4 Important services in depth

#### Application performance and core network
- **CDN and caching:** caches static content at the edge to reduce latency and origin load. Controlled with Cache Rules and Cache-Control headers; **Tiered Cache** reduces origin requests further.
- **DNS:** a fast, globally distributed authoritative DNS service, free for domains using Cloudflare, with DNSSEC support. Cloudflare also operates the public resolver 1.1.1.1.
- **Registrar:** register domains at wholesale price.
- **Load Balancing and Argo Smart Routing:** health-checked traffic steering across origins and optimized routing across Cloudflare's backbone.
- **Images and Stream:** image optimization and resizing on the fly, and video storage, encoding and delivery.

#### Security
- **DDoS protection:** automatic L3/L4 and L7 mitigation, always on, included on every plan.
- **WAF (Web Application Firewall):** managed rulesets (including OWASP protections) and custom rules.
- **Bot management, Rate limiting, Turnstile:** detect and block bad bots, limit abuse, and a privacy-friendly CAPTCHA alternative.
- **SSL/TLS:** free certificates and encryption modes (Off, Flexible, Full, Full strict). Full (strict) is recommended because it encrypts and validates the connection to the origin.
- **API Shield, Page Shield, Email security:** API protection, client-side script monitoring and phishing protection.

#### Zero Trust (SASE)
- **Cloudflare Access:** put a login in front of internal applications without a VPN.
- **Gateway:** DNS and HTTP filtering for users and devices. **WARP:** device client for secure connectivity.
- **Cloudflare Tunnel (`cloudflared`):** creates an outbound-only encrypted connection from your server to Cloudflare, so you can publish a service without opening inbound ports or exposing a public IP.
- **Magic WAN / Magic Transit:** network-level connectivity and DDoS protection for entire IP networks.

#### Developer platform
- **Workers:** serverless JavaScript, TypeScript, Python and WebAssembly functions that run at the edge on V8 isolates. Isolates start in milliseconds, so there is essentially no cold-start delay compared with container-based functions. Used for APIs, request routing, A/B testing, authentication and full applications.
- **Pages:** hosting for static sites and full-stack frameworks with Git-based deploys and preview URLs for every branch (Cloudflare is increasingly steering new projects toward Workers with static assets).
- **R2:** S3-compatible object storage with **no egress fees**, which can significantly cut costs for data-heavy applications.
- **D1:** serverless SQL database based on SQLite. **KV:** global key-value store optimized for read-heavy data with eventual consistency. **Durable Objects:** strongly consistent, stateful objects for coordination such as chat rooms or counters. **Queues:** message queues for Workers. **Hyperdrive:** accelerates connections from Workers to existing databases such as PostgreSQL.
- **Workers AI, Vectorize, AI Gateway, AI Search:** run open-source AI models on Cloudflare's GPUs, vector database for embeddings, and an observability/proxy layer for AI API calls.
- **Cloudflare Containers, Workflows, Cron Triggers, Email Routing:** run containers, durable multi-step workflows, scheduled jobs and email forwarding.

#### Analytics and observability
- **Analytics dashboards, Web Analytics (privacy-friendly, no cookies), Logpush, Workers Logs and Observability, Radar** (public internet trends and outage data).

### 5.5 Example architecture: a fast, protected website with an edge API
1. The domain uses **Cloudflare DNS**; traffic is proxied through the network.
2. **DDoS protection, WAF and rate limiting** filter bad traffic first.
3. **CDN** serves cached static assets directly from the nearest data center.
4. API requests are handled by a **Worker**, which reads configuration from **KV**, queries **D1** for data and stores uploads in **R2**.
5. Anything else is forwarded to an existing **origin server on AWS/Azure/GCP**, connected securely through **Cloudflare Tunnel**.
6. Admin pages are protected using **Cloudflare Access**.

### 5.6 Pricing model and free usage
- **Free plan** for websites covering DNS, CDN, SSL and DDoS protection; paid plans (Pro, Business, Enterprise) add advanced WAF, support, SLAs and features.
- **Workers:** a free allowance of requests per day, with a paid plan billed on requests and CPU time.
- **R2:** free monthly allowance, then billed by storage and operations, with **zero egress fees**.
- **D1, KV, Pages, Queues:** each has a free tier with limits; check the pricing pages for current figures: https://www.cloudflare.com/plans/ and https://developers.cloudflare.com/workers/platform/pricing/.
- A free account needs only an email address and no credit card for the free tier.

### 5.7 Official documentation and learning resources
- Documentation (very well organized per product, with quickstarts and tutorials): https://developers.cloudflare.com
- **Cloudflare Learning Center** (excellent plain-language explanations of networking and security concepts such as DNS, DDoS, CDN, WAF and Zero Trust): https://www.cloudflare.com/learning/
- Workers documentation, examples and templates: https://developers.cloudflare.com/workers/
- Reference architectures and design guides: https://developers.cloudflare.com/reference-architecture/
- Cloudflare Blog (deep technical write-ups on how the network works): https://blog.cloudflare.com
- Cloudflare Radar: https://radar.cloudflare.com

### 5.8 Strengths and limitations
**Strengths:** very easy to get started, free tier is generous, excellent performance and security out of the box, no cold starts on Workers, R2 with no egress fees, and a simple pricing story.
**Limitations:** not a full cloud (no general-purpose VMs, and a narrower database and managed-service catalog), the Workers runtime has its own limits and differences from traditional servers, and enterprise features and support sit on higher plans.

### 5.9 What I explored
Browsed the documentation, the product catalog and the Learning Center: how proxying and DNS work, the difference between SSL modes, and what Workers, Pages, R2, D1 and KV are for.

---

## 6. Comparison of the four platforms

Now that each platform has been covered individually, this section compares them directly.

### 6.1 At a glance

| Aspect | AWS | Azure | GCP | Cloudflare |
|---|---|---|---|---|
| **Launched** | 2006 | 2010 | 2008 (App Engine), broader platform later | 2009 |
| **Type** | Full-service public cloud | Full-service public cloud | Full-service public cloud | Edge network, security and developer platform |
| **Market position** | Largest | Second largest | Third | Specialist; very large CDN and security footprint |
| **Core identity** | Breadth and maturity | Enterprise and Microsoft integration | Data, AI and Kubernetes | Speed, security and the edge |
| **Parent hierarchy** | Organization > Account | Tenant > Mgmt Group > Subscription > Resource Group | Organization > Folder > Project | Account > Zone / resources |
| **Network model** | Regional VPCs | Regional VNets | Global VPC | Global anycast edge, no regions to choose |
| **CLI** | `aws` | `az` | `gcloud` | `wrangler` |
| **IaC (native)** | CloudFormation, CDK | ARM, Bicep | Infrastructure Manager | Terraform provider, Wrangler config |

### 6.2 Service equivalents

| Need | AWS | Azure | GCP | Cloudflare |
|---|---|---|---|---|
| Virtual machines | EC2 | Virtual Machines | Compute Engine | Not offered |
| Serverless functions | Lambda | Azure Functions | Cloud Functions / Cloud Run functions | Workers |
| Serverless containers | Fargate / App Runner | Container Apps | Cloud Run | Containers |
| Managed Kubernetes | EKS | AKS | GKE | Not offered |
| PaaS web hosting | Elastic Beanstalk / Amplify | App Service | App Engine / Cloud Run | Pages / Workers |
| Container registry | ECR | Container Registry | Artifact Registry | Not offered (use external registry) |
| Object storage | S3 | Blob Storage | Cloud Storage | R2 |
| Block storage | EBS | Managed Disks | Persistent Disk | Not offered |
| File storage | EFS / FSx | Azure Files | Filestore | Not offered |
| Relational database | RDS / Aurora | Azure SQL / Azure DB for PostgreSQL, MySQL | Cloud SQL / AlloyDB / Spanner | D1 (SQLite-based) |
| NoSQL | DynamoDB | Cosmos DB | Firestore / Bigtable | KV / Durable Objects |
| Cache | ElastiCache | Azure Cache for Redis | Memorystore | KV / Cache API |
| Data warehouse | Redshift | Synapse / Fabric | BigQuery | Not offered (Pipelines / R2 SQL emerging) |
| Messaging / queues | SQS / SNS / EventBridge | Service Bus / Event Grid | Pub/Sub | Queues |
| Private network | VPC | VNet | VPC | Tunnel / Magic WAN |
| DNS | Route 53 | Azure DNS | Cloud DNS | Cloudflare DNS |
| CDN | CloudFront | Front Door / Azure CDN | Cloud CDN | Cloudflare CDN |
| Load balancer | ELB (ALB/NLB) | Load Balancer / Application Gateway | Cloud Load Balancing | Load Balancing |
| WAF / DDoS | AWS WAF / Shield | Azure WAF / DDoS Protection | Cloud Armor | WAF / DDoS (built in) |
| Identity | IAM / IAM Identity Center | Entra ID + RBAC | Cloud IAM / Identity Platform | Access / Zero Trust |
| Secrets | Secrets Manager | Key Vault | Secret Manager | Workers Secrets / Secrets Store |
| Monitoring | CloudWatch | Azure Monitor | Cloud Monitoring | Analytics / Logs / Observability |
| Audit logs | CloudTrail | Activity Log | Cloud Audit Logs | Audit Logs |
| CI/CD | CodePipeline / CodeBuild | Azure DevOps / GitHub Actions | Cloud Build / Cloud Deploy | Workers Builds / Pages |
| AI platform | SageMaker / Bedrock | Azure AI Foundry / Azure OpenAI | Vertex AI / Gemini | Workers AI / AI Gateway |
| Cost tools | Cost Explorer / Budgets | Cost Management | Billing reports / Budgets | Billing / usage dashboards |

### 6.3 Compute
All three big clouds offer VMs, containers, Kubernetes and serverless functions. AWS has the largest variety of instance types and compute options. Azure stands out for Windows workloads and licensing savings through Hybrid Benefit. GCP's Cloud Run is regarded as one of the simplest ways to run containers serverlessly, and GKE is a leader for Kubernetes. Cloudflare takes a different approach: Workers run on lightweight isolates at the edge with practically no cold starts, but they are not suited to long-running or heavy workloads the way VMs are.

### 6.4 Storage and databases
S3, Blob Storage and Cloud Storage are very similar (buckets or containers holding objects, with hot-to-archive tiers). R2 matches the S3 API but charges no egress fees, which is its main differentiator. For databases, AWS has the widest set of purpose-built engines, Azure is strongest for SQL Server and has the multi-model Cosmos DB, and GCP has Spanner (global relational consistency) and BigQuery (analytics). Cloudflare's D1 and KV are simpler and designed for edge applications rather than large, complex data platforms.

### 6.5 Networking and global reach
AWS and Azure use regional virtual networks; GCP's VPC is global and its premium network tier keeps traffic on Google's backbone. Cloudflare's network is the largest of the four in number of locations and is where CDN, DNS and DDoS protection are strongest, since that is its core business. This is why Cloudflare is often placed in front of workloads that live on the other three.

### 6.6 Security and identity
All four support encryption, WAF, DDoS protection, secret storage and compliance certifications. AWS IAM is powerful and granular but has a learning curve. Azure's Entra ID is the strongest identity platform for organizations that already use Microsoft 365. GCP's IAM is simple and consistent with roles on a resource hierarchy. Cloudflare's security is built in at the network edge and its Zero Trust products (Access, Gateway, Tunnel) are a modern alternative to traditional VPNs.

### 6.7 Data, analytics and AI
GCP is the strongest for analytics (BigQuery) and offers its own AI chips (TPUs) and Gemini models. AWS offers the broadest set of data and ML services (SageMaker, Bedrock, Redshift, Glue). Azure has a close relationship with OpenAI models and integrates with Microsoft Fabric and Power BI. Cloudflare provides lightweight AI inference at the edge (Workers AI) and an AI Gateway for managing AI API traffic, rather than a full ML training platform.

### 6.8 Pricing and free usage

| Aspect | AWS | Azure | GCP | Cloudflare |
|---|---|---|---|---|
| Billing granularity | Per second or hour depending on service | Per second or hour | Per second (many services) | Per request / usage, or flat plan |
| Discount options | Savings Plans, Reserved, Spot | Reservations, Savings Plans, Spot, Hybrid Benefit | Sustained use (automatic), Committed use, Spot | Plan tiers; mostly usage-based |
| Egress (data out) | Charged | Charged | Charged | R2 has no egress fees; CDN bandwidth generally not metered on standard plans |
| Free offering | Free Tier / free plan for new accounts | Free account with credit and always-free services | Trial credit and Always Free tier | Free plan and free allowances for developer products, no card needed |
| Cost estimator | AWS Pricing Calculator | Azure Pricing Calculator | Google Cloud Pricing Calculator | Plans and pricing pages |
| Pricing complexity | High | High | Medium | Low to medium |

### 6.9 Learning and documentation

| | AWS | Azure | GCP | Cloudflare |
|---|---|---|---|---|
| Docs quality | Extensive, sometimes dense | Extensive, well structured | Clear, with good quickstarts | Very clear, product-focused |
| Free hands-on learning | Skill Builder, Workshops | Microsoft Learn sandbox | Cloud Skills Boost labs | Docs tutorials, Learning Center |
| Entry certification | Cloud Practitioner | AZ-900 | Cloud Digital Leader | No traditional equivalent |
| Community size | Largest | Large | Medium | Growing, strong developer community |

### 6.10 Strengths and best fit

| Platform | Best suited for | Watch out for |
|---|---|---|
| **AWS** | Almost any workload; startups to large enterprises; teams wanting the most services and community support | Complexity and many overlapping services; egress costs |
| **Azure** | Organizations using Microsoft products; hybrid cloud; .NET and Windows workloads | Sprawling portal and naming changes |
| **GCP** | Data analytics, machine learning, Kubernetes and container-first teams | Smaller ecosystem and fewer legacy-enterprise services |
| **Cloudflare** | Fast and secure websites and APIs, DDoS/WAF protection, edge applications, Zero Trust access, low-cost storage with no egress fees | Not a full cloud replacement; limited to its own runtime and managed services |

### 6.11 Which one to choose? (a practical view)
- **Learning cloud fundamentals for the first time:** start with AWS (largest market and most learning content) or Azure (very structured Microsoft Learn paths) and learn the shared concepts, since they transfer.
- **Company already on Microsoft 365 and Windows Server:** Azure.
- **Data warehouse, ML or Kubernetes-heavy project:** GCP.
- **Need performance and protection for a website or API with minimal setup:** Cloudflare, and it can be used in addition to any of the others.
- **Real-world pattern:** many production systems combine them, for example an app running on AWS or GCP with Cloudflare in front for DNS, CDN and security.

### 6.12 Key takeaways from the comparison
1. AWS, Azure and GCP offer largely equivalent services with different names, so skills in one transfer to the others.
2. Their differences are mainly ecosystem fit (Microsoft vs Google vs breadth), strengths (analytics, hybrid, maturity) and pricing details.
3. Cloudflare is not a direct competitor to the big three. It complements them by handling the edge, networking and security layers.
4. The best choice depends on existing tools, team skills, workload type, compliance and budget, not on one platform being universally "best".

---

## 7. How these platforms are used in DevOps

- **Infrastructure as Code:** Terraform works with all four providers and is the most portable skill; each big cloud also has a native IaC tool.
- **CI/CD:** each has its own pipeline service, and GitHub Actions or Jenkins can deploy to any of them.
- **Containers and Kubernetes:** Docker images run on ECS/EKS, AKS/Container Apps and Cloud Run/GKE; Cloudflare Workers handle lightweight edge logic.
- **Observability:** CloudWatch, Azure Monitor and Cloud Monitoring provide metrics, logs and alerts; Cloudflare provides edge analytics and logs.
- **Security (DevSecOps):** least-privilege IAM, MFA, secret managers instead of hard-coded credentials, encryption at rest and in transit, WAF and DDoS protection.
- **Cost management (FinOps):** budgets and alerts, resource tagging, right-sizing, and shutting down unused resources on every platform.
- **Typical pipeline:** code is pushed to Git, a CI job builds and tests it and produces a container image, the image goes to a registry (ECR, ACR or Artifact Registry), and a deployment step rolls it out to ECS/AKS/Cloud Run/Kubernetes, with Cloudflare handling DNS and edge security in front.

---

## 8. Summary and my findings

Going through AWS, Azure, GCP and Cloudflare showed me that the three big clouds are built from the same basic pieces: compute, storage, databases, networking, identity, monitoring and AI services. They just use different names, so learning one platform makes the others much easier to pick up. AWS stood out for its sheer breadth, maturity and community support. Azure stood out for its integration with the Microsoft ecosystem and its identity platform (Microsoft Entra ID). GCP stood out for data analytics with BigQuery, for Kubernetes, and for how simple Cloud Run makes deploying containers.

Cloudflare was the most different one. It is not a full cloud like the other three, but an edge network focused on speed and security. What surprised me most was that R2 storage has no egress fees and that Workers start in milliseconds with no cold-start delay. It also made clear that Cloudflare is usually used together with the big three rather than instead of them, for example as the DNS, CDN and security layer in front of an app hosted on AWS or GCP.

My main takeaway is that no platform is the best for everything. The right choice depends on the existing tools, the type of workload, the team's skills and the budget. The services I would like to try first, once it is safe and free to do so, are Lambda with S3 on AWS, Cloud Run on GCP, and Workers with Pages on Cloudflare, because they are the quickest way to see how each platform thinks about deploying an application. For next steps I want to work through the free learning paths (AWS Skill Builder, Microsoft Learn, Google Cloud Skills Boost and the Cloudflare Learning Center), start with the AWS Cloud Practitioner or AZ-900 material, and learn Terraform so I can apply this to DevOps work such as automating deployments.