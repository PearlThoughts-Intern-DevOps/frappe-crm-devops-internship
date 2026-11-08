Task 4: Cloud Platform Exploration

1. Introduction

The objective of this task was to explore four major cloud platforms:

Amazon Web Services (AWS)

Microsoft Azure

Google Cloud Platform (GCP)

Cloudflare

During this task, I revised the AWS services and concepts that I had already learned, explored the basic services offered by Microsoft Azure and Google Cloud Platform, and explored Cloudflare to understand its services and how it helps improve website performance, security, and reliability.

I referred to the official documentation and learning resources of each platform to understand their services, purposes, and practical applications.

2. Amazon Web Services (AWS)

Overview

Amazon Web Services (AWS) is a cloud computing platform that provides services for computing, storage, networking, databases, security, container management, notifications, and application deployment.

Since I had already learned about AWS previously, I used this task to revise the important services and refresh my understanding of their purposes and use cases.

AWS Services Revised

Service

Full Form

Purpose and Usage

EC2

Elastic Compute Cloud

Provides virtual servers for hosting applications and websites.

S3

Simple Storage Service

Object storage for files, images, backups, and static content.

IAM

Identity and Access Management

Manages users, roles, policies, and permissions.

VPC

Virtual Private Cloud

Provides an isolated virtual network for AWS resources.

RDS

Relational Database Service

Provides managed relational databases such as MySQL and PostgreSQL.

Lambda

AWS Lambda

Runs code without managing servers.

CloudWatch

Amazon CloudWatch

Monitors AWS resources, application metrics, logs, and alarms.

EBS

Elastic Block Store

Provides persistent block storage volumes for EC2 instances.

ECR

Elastic Container Registry

Stores and manages Docker container images.

ECS

Elastic Container Service

Deploys and manages containerized applications.

ALB

Application Load Balancer

Distributes HTTP and HTTPS traffic across application targets.

Auto Scaling

EC2 Auto Scaling

Automatically increases or decreases the number of EC2 instances based on demand.

SNS

Simple Notification Service

Sends notifications through email, SMS, and application integrations.

ELB

Elastic Load Balancing

Distributes incoming traffic across multiple targets.

Important AWS Concepts Revised

1. Compute Services

EC2 (Elastic Compute Cloud)

EC2 provides virtual machines in the AWS cloud. It allows users to launch instances with different operating systems and configurations.

Uses:

Hosting websites and applications.

Running backend services.

Deploying application servers.

Running development and testing environments.

Lambda

Lambda is a serverless computing service that allows developers to execute code without managing servers.

Uses:

Running background tasks.

Processing files.

Handling application events.

Building serverless applications.

2. Storage Services

S3 (Simple Storage Service)

S3 is an object storage service used to store and retrieve data.

Uses:

Storing images and documents.

Application file storage.

Database backups.

Static website assets.

EBS (Elastic Block Store)

EBS provides persistent block storage volumes for EC2 instances.

Uses:

Storing application data.

Hosting operating system volumes.

Providing storage for databases running on EC2.

3. Networking Services

VPC (Virtual Private Cloud)

VPC provides an isolated networking environment within AWS.

Important concepts:

Public and private subnets.

Route tables.

Internet Gateway.

NAT Gateway.

Security Groups.

Network ACLs.

ALB (Application Load Balancer)

ALB distributes incoming HTTP and HTTPS traffic across multiple targets, such as EC2 instances and containers.

Uses:

Distributing application traffic.

Supporting path-based and host-based routing.

Improving application availability.

ELB (Elastic Load Balancing)

ELB is the AWS service family for distributing incoming traffic across multiple targets. It includes different load balancer types, including Application Load Balancer.

4. Container Services

ECR (Elastic Container Registry)

ECR is a managed container image registry.

Uses:

Storing Docker images.

Managing container image repositories.

Providing container images to ECS deployments.

ECS (Elastic Container Service)

ECS is a container orchestration service used to deploy and manage containerized applications.

Important concepts:

Clusters.

Task Definitions.

Tasks.

Services.

Container instances and capacity providers.

Uses:

Deploying Docker containers.

Managing containerized applications.

Scaling container workloads.

5. Auto Scaling

EC2 Auto Scaling automatically adjusts the number of EC2 instances based on application requirements.

Uses:

Increasing instances when traffic increases.

Reducing instances when demand decreases.

Maintaining application availability.

Managing infrastructure capacity.

6. Security and Identity

IAM (Identity and Access Management)

IAM helps manage access to AWS resources.

Important concepts:

IAM Users.

IAM Groups.

IAM Roles.

IAM Policies.

It helps ensure that users and services have only the permissions they need.

7. Database Services

RDS (Relational Database Service)

RDS is a managed relational database service.

It supports database engines such as:

MySQL.

PostgreSQL.

MariaDB.

Microsoft SQL Server.

Oracle.

Uses:

Hosting application databases.

Managing relational data.

Automated backups and maintenance.

8. Monitoring and Notifications

CloudWatch

CloudWatch helps monitor AWS resources and applications.

Uses:

Monitoring CPU utilization.

Collecting application logs.

Creating alarms.

Tracking resource performance.

SNS (Simple Notification Service)

SNS is a messaging and notification service.

Uses:

Sending email notifications.

Sending SMS notifications.

Publishing messages to subscribers.

Integrating notifications with other AWS services.

What I Revised in AWS

I revised the major AWS services and refreshed my understanding of their purposes and practical use cases.

I specifically focused on EC2, S3, IAM, VPC, RDS, Lambda, CloudWatch, EBS, ECR, ECS, ALB, ELB, Auto Scaling, and SNS.

I also revised how ECR and ECS work together to deploy containerized applications, how ALB distributes incoming application traffic, how Auto Scaling manages EC2 capacity, and how SNS sends notifications.

This revision helped strengthen my existing AWS knowledge and improve my understanding of how different AWS services work together when deploying and managing applications.

AWS Learning Resources

AWS Documentation: https://aws.amazon.com/documentation-overview/

AWS Getting Started: https://aws.amazon.com/getting-started/

AWS Skill Builder: https://skillbuilder.aws/

3. Microsoft Azure

Overview

Microsoft Azure is Microsoft's cloud computing platform. It provides services for building, deploying, and managing applications through Microsoft's global cloud infrastructure.

As part of this task, I explored the basic Azure services and understood their purposes and use cases.

I also compared some Azure services with the AWS services I had previously learned.

Basic Azure Services Explored

Service

Purpose

Usage

Azure Virtual Machines

Provides virtual machines in Azure.

Hosting applications and operating systems.

Azure Blob Storage

Object storage service.

Storing images, documents, videos, and backups.

Azure Virtual Network (VNet)

Provides private networking.

Connecting and isolating Azure resources.

Microsoft Entra ID

Identity and access management.

Managing users, authentication, and access.

Azure SQL Database

Managed relational database.

Hosting SQL databases.

Azure Functions

Serverless computing service.

Running event-driven code without managing servers.

Azure App Service

Managed application hosting platform.

Hosting web applications and APIs.

Azure Monitor

Monitoring service.

Monitoring application and infrastructure performance.

Important Concepts Explored

1. Compute Services

Azure Virtual Machines

Azure Virtual Machines provide computing resources in the cloud.

Uses:

Hosting websites and applications.

Running backend services.

Creating development environments.

Azure App Service

Azure App Service is a managed platform for hosting web applications and APIs.

Uses:

Hosting web applications.

Deploying backend APIs.

Managing application hosting without directly managing virtual machines.

Azure Functions

Azure Functions provides serverless computing.

Uses:

Executing code based on events.

Running background jobs.

Processing application requests.

2. Storage Services

Azure Blob Storage

Azure Blob Storage is an object storage service used to store unstructured data.

Uses:

Storing images and documents.

Application file storage.

Storing backups.

Managing large amounts of unstructured data.

3. Networking Services

Azure Virtual Network (VNet)

Azure Virtual Network provides an isolated networking environment for Azure resources.

Important concepts:

Virtual networks.

Subnets.

Network connectivity.

Network security.

4. Identity and Security

Microsoft Entra ID

Microsoft Entra ID provides identity and access management.

Uses:

Managing user identities.

User authentication.

Application access management.

Integrating identity with cloud services.

Azure RBAC can be used to control access to Azure resources through role assignments.

5. Database Services

Azure SQL Database

Azure SQL Database is a managed relational database service.

Uses:

Hosting relational databases.

Storing application data.

Managing SQL-based applications.

6. Monitoring Services

Azure Monitor

Azure Monitor helps monitor cloud infrastructure and application performance.

Uses:

Collecting metrics.

Analyzing logs.

Monitoring application health.

Identifying performance issues.

AWS and Azure Service Comparison

AWS Service

Similar Azure Service

EC2

Azure Virtual Machines

S3

Azure Blob Storage

VPC

Azure Virtual Network

IAM

Microsoft Entra ID and Azure RBAC

RDS

Azure SQL Database

Lambda

Azure Functions

CloudWatch

Azure Monitor

Note: These services have similar purposes, but their features and implementations are not always identical.

What I Learned About Azure

I explored the basic services offered by Microsoft Azure and understood how they are used for computing, storage, networking, databases, identity management, and monitoring.

I also compared Azure services with AWS services to understand how different cloud providers offer similar solutions using different service names and management tools.

Azure Learning Resources

Azure Documentation: https://learn.microsoft.com/en-us/azure/

Azure Fundamentals: https://learn.microsoft.com/en-us/training/azure/

Azure Products: https://azure.microsoft.com/en-us/products

Azure Fundamentals Learning Path: https://learn.microsoft.com/en-us/credentials/certifications/azure-fundamentals/

4. Google Cloud Platform (GCP)

Overview

Google Cloud Platform (GCP), also known as Google Cloud, is Google's cloud computing platform.

It provides services for application hosting, storage, networking, databases, analytics, machine learning, and application development.

For this task, I explored the basic GCP services and understood their main purposes and use cases.

Basic GCP Services Explored

Service

Purpose

Usage

Compute Engine

Provides virtual machines.

Hosting applications and workloads.

Cloud Storage

Object storage service.

Storing files, images, backups, and other data.

Cloud Run

Serverless container platform.

Running containerized applications without managing servers.

Cloud Functions

Event-driven serverless computing.

Running code in response to events.

Cloud SQL

Managed relational database.

Hosting MySQL, PostgreSQL, and SQL Server databases.

Cloud IAM

Identity and Access Management.

Managing users, roles, and permissions.

VPC

Virtual Private Cloud networking.

Managing private networks and connectivity.

BigQuery

Data warehouse and analytics service.

Analyzing large datasets using SQL.

Cloud Monitoring

Monitoring and observability service.

Monitoring applications and cloud resources.

Important Concepts Explored

1. Compute Services

Compute Engine

Compute Engine provides virtual machines for running applications and workloads.

Uses:

Hosting websites.

Running backend applications.

Creating virtual machine environments.

Cloud Run

Cloud Run provides a managed platform for deploying containerized applications.

Uses:

Deploying container-based applications.

Hosting APIs.

Running web applications without managing servers.

Cloud Functions

Cloud Functions provides event-driven serverless computing.

Uses:

Running code in response to events.

Processing files.

Executing background tasks.

2. Storage Services

Cloud Storage

Cloud Storage is an object storage service used to store unstructured data.

Uses:

Storing images and files.

Application data storage.

Backup storage.

Managing large amounts of data.

3. Networking Services

Google Cloud VPC

VPC provides virtual networking for Google Cloud resources.

Important concepts:

Virtual networks.

Subnets.

Firewall rules.

Network connectivity.

4. Identity and Security

Cloud IAM

Cloud IAM manages permissions and access to Google Cloud resources.

Uses:

Managing users and service accounts.

Assigning roles.

Controlling access to cloud resources.

Applying permission policies.

5. Database Services

Cloud SQL

Cloud SQL is a managed relational database service.

It supports:

MySQL.

PostgreSQL.

SQL Server.

Uses:

Hosting application databases.

Managing relational data.

Reducing database administration overhead.

6. Analytics Services

BigQuery

BigQuery is a serverless data warehouse and analytics platform.

Uses:

Analyzing large datasets.

Running SQL queries.

Generating reports.

Performing data analytics.

7. Monitoring Services

Cloud Monitoring

Cloud Monitoring helps monitor cloud resources and application performance.

Uses:

Monitoring resource metrics.

Tracking application performance.

Creating alerts.

Identifying infrastructure issues.

AWS and GCP Service Comparison

AWS Service

Similar GCP Service

EC2

Compute Engine

S3

Cloud Storage

VPC

Google Cloud VPC

IAM

Cloud IAM

RDS

Cloud SQL

Lambda

Cloud Run Functions

CloudWatch

Cloud Monitoring

Note: These are conceptual alternatives based on similar purposes. Their features and implementations may differ.

What I Learned About GCP

I explored the basic services available in Google Cloud Platform and understood their purposes and use cases.

I focused on compute, storage, networking, databases, identity management, serverless computing, and analytics.

I also compared GCP services with AWS services to understand the similarities between the platforms and how applications can be hosted and managed using Google Cloud.

GCP Learning Resources

Google Cloud Documentation: https://docs.cloud.google.com/

Google Cloud Products: https://cloud.google.com/products

Google Cloud Training: https://cloud.google.com/learn/training

Google Cloud Skills Boost: https://www.cloudskillsboost.google/

5. Cloudflare

Overview

Cloudflare is a cloud platform that provides website security, performance optimization, DNS management, and edge computing services.

Services Explored

Service

Purpose

DNS

Manages domain names and DNS records.

CDN

Improves website loading speed.

SSL/TLS

Secures website communication through HTTPS.

WAF

Protects websites from malicious requests.

DDoS Protection

Protects applications from traffic attacks.

Workers

Runs serverless code at the edge.

Pages

Hosts websites and frontend applications.

R2

Provides object storage.

Zero Trust

Provides secure access to applications.

What I Learned

I explored Cloudflare's basic services and understood how they improve website performance, security, and reliability. I also learned about DNS, CDN, SSL/TLS, WAF, DDoS Protection, and edge computing.

Cloudflare Learning Resources

Documentation: https://developers.cloudflare.com/

Learning Center: https://www.cloudflare.com/learning/

Products: https://www.cloudflare.com/products/

6. Comparison of All Four Platforms

The following table summarizes the major services and their equivalent or similar services across the platforms.

Category

AWS

Azure

GCP

Cloudflare

Virtual Machines

EC2

Azure VM

Compute Engine

No direct general-purpose VM equivalent

Object Storage

S3

Blob Storage

Cloud Storage

R2

Networking

VPC

Virtual Network

VPC

Cloudflare Network

Identity

IAM

Entra ID / Azure RBAC

Cloud IAM

Zero Trust / Access

Serverless

Lambda

Azure Functions

Cloud Functions

Workers

Relational Database

RDS

Azure SQL Database

Cloud SQL

No direct general-purpose equivalent

Container Registry

ECR

Azure Container Registry

Artifact Registry

No direct equivalent

Container Management

ECS

Azure container services

Cloud Run

Workers

Monitoring

CloudWatch

Azure Monitor

Cloud Monitoring

Analytics and observability tools

Website Security

AWS WAF / Shield

Azure security services

Cloud Armor

WAF / DDoS Protection

CDN

CloudFront

Azure Front Door / CDN

Cloud CDN

Cloudflare CDN

Observation:

AWS, Azure, and GCP provide broad cloud infrastructure and platform services, including compute, storage, databases, networking, and application hosting.

Cloudflare focuses more on improving application delivery, security, DNS, edge computing, and connectivity.

Although many services have similar purposes, their configurations, pricing, architecture, and capabilities differ.

7. Practical Understanding: How Cloud Services Work Together

To understand the role of different cloud services, I reviewed a basic web application architecture.

A typical application deployment can involve the following components:

A domain name is configured using a DNS service.

A user sends a request to access the website.

A CDN can deliver cached static content.

A load balancer distributes incoming requests.

Compute services such as EC2, Azure Virtual Machines, or Compute Engine run the application.

Object storage such as S3, Blob Storage, or Cloud Storage stores static files and application assets.

A database service stores application data.

IAM controls access to cloud resources.

Monitoring services collect logs and metrics to track application performance.

Cloudflare can also be placed in front of an application to provide DNS, CDN, SSL/TLS, and security protection.

For AWS, I also revised how ECR stores container images, ECS runs containerized applications, ALB distributes incoming traffic, Auto Scaling adjusts compute capacity, and SNS sends notifications.

This helped me understand that cloud services are not independent components; they work together to build, secure, deploy, and maintain applications.