Task 4: Cloud Platform Exploration
Sahil Shaikh 

1. Introduction

Cloud computing is the delivery of computing services such as servers, storage, databases, networking, software and security over the internet.

Instead of purchasing and maintaining physical servers, companies can rent computing resources from cloud service providers whenever they need them.

Cloud computing helps organisations reduce infrastructure costs, improve flexibility, scale applications and access technology from anywhere.

Objectives

The objectives of this task are:

* To explore AWS (Amazon Web Services).
* To understand Microsoft Azure and its cloud services.
* To explore Google Cloud Platform (GCP).
* To understand Cloudflare and its security and performance services.
* To compare the features and applications of all four platforms.
* To identify how these platforms are useful in cloud computing and DevOps.

⸻

2. Amazon Web Services (AWS)

2.1 Overview

Amazon Web Services (AWS) is a cloud computing platform provided by Amazon. It offers a wide range of services for computing, storage, databases, networking, security, monitoring and application deployment.

AWS allows businesses and developers to build, deploy and manage applications without purchasing physical hardware.

It is widely used by startups, enterprises, developers and organisations to host websites, manage applications, store information and run large-scale systems.

2.2 Important AWS Services

Service	Description	Purpose
Amazon EC2	Elastic Compute Cloud provides virtual servers in the cloud.	Running websites, applications and software.
Amazon S3	Simple Storage Service provides scalable object storage.	Storing files, images, videos and backups.
AWS IAM	Identity and Access Management manages users, roles and permissions.	Controlling access to AWS resources.
Amazon RDS	Relational Database Service provides managed relational databases.	Storing and managing structured information.
AWS Lambda	A serverless computing service that executes code in response to events.	Running code without managing servers.
Amazon VPC	Virtual Private Cloud provides an isolated virtual network.	Managing network resources securely.
Amazon CloudWatch	Monitoring and observability service.	Monitoring system performance, logs and alerts.
Elastic Load Balancing	Distributes incoming traffic across multiple targets.	Improving application availability and performance.
Amazon ECR	Elastic Container Registry stores container images.	Storing and managing Docker images.
Amazon ECS	Elastic Container Service runs and manages containers.	Deploying containerised applications.
Amazon EKS	Elastic Kubernetes Service provides managed Kubernetes.	Managing Kubernetes-based applications.

2.3 Practical Example

Consider an organisation developing an online shopping website.

* EC2 can be used to run the website.
* S3 can store product images and documents.
* RDS can store customer details, orders and product information.
* IAM can control which employees are allowed to access resources.
* CloudWatch can monitor server performance and application errors.
* Elastic Load Balancing can distribute incoming traffic across multiple servers.

By combining these services, the organisation can build a scalable and reliable application.

2.4 Advantages of AWS

1. Scalability: Resources can be increased or decreased according to application requirements.
2. Flexibility: It provides many services for different computing needs.
3. Global Infrastructure: AWS operates infrastructure in multiple geographic regions.
4. Security: Provides identity management, encryption and network security features.
5. Cost Management: Supports pay-as-you-go pricing for many services.
6. DevOps Integration: Supports automation, containers, monitoring and continuous deployment workflows.

2.5 Limitations of AWS

* The number of available services can make it difficult for beginners.
* Incorrect resource configurations can result in unexpected costs.
* Managing complex cloud environments requires technical knowledge.
* Organisations must understand security responsibilities and permissions.

2.6 Learning Resources

* AWS Official Website: https://aws.amazon.com/
* AWS Documentation: https://docs.aws.amazon.com/
* AWS Skill Builder: https://skillbuilder.aws/
* AWS Getting Started: https://aws.amazon.com/getting-started/

⸻

3. Microsoft Azure

3.1 Overview

Microsoft Azure is a cloud computing platform developed by Microsoft. It provides services for application development, virtual machines, databases, networking, storage, analytics and security.

Azure allows organisations to build, deploy and manage applications using Microsoft’s global cloud infrastructure.

It is particularly useful for organisations that already use Microsoft technologies such as Windows Server, Microsoft 365 and Active Directory.

3.2 Important Azure Services

Service	Description	Purpose
Azure Virtual Machines	Provides virtual computers in the cloud.	Running applications and operating systems.
Azure Blob Storage	Object storage for unstructured data.	Storing images, documents, videos and backups.
Azure SQL Database	Managed relational database service.	Storing structured application data.
Azure Functions	Event-driven serverless computing service.	Running code without managing servers.
Microsoft Entra ID	Identity and access management service.	Managing users, authentication and permissions.
Azure Virtual Network	Provides private networking in Azure.	Connecting and isolating cloud resources.
Azure Monitor	Monitoring and observability platform.	Tracking application and infrastructure performance.
Azure Kubernetes Service (AKS)	Managed Kubernetes service.	Deploying and managing containerised applications.
Azure App Service	Managed platform for hosting web applications and APIs.	Hosting websites and web applications.
Azure Key Vault	Securely stores keys, secrets and certificates.	Protecting passwords, credentials and encryption keys.

3.3 Practical Example

Consider a company developing an employee management application.

* Azure Virtual Machines can run the application.
* Azure SQL Database can store employee information.
* Blob Storage can store employee documents.
* Microsoft Entra ID can manage employee logins and access permissions.
* Azure Monitor can track the application’s performance.
* Azure Key Vault can securely store application credentials.

These services help the organisation manage its application infrastructure securely.

3.4 Advantages of Microsoft Azure

1. Microsoft Integration: Works well with Microsoft’s existing software and enterprise technologies.
2. Scalability: Resources can be adjusted according to workload requirements.
3. Security: Provides identity management, encryption and security monitoring.
4. Hybrid Cloud: Supports integration between on-premises infrastructure and cloud services.
5. DevOps Support: Integrates with GitHub and Azure DevOps for software development and deployment.
6. Enterprise Support: Provides services suitable for large organisations.

3.5 Limitations of Microsoft Azure

* Some services and configurations can be difficult for beginners.
* Complex pricing structures require careful cost management.
* Organisations need to understand identity and access configurations.
* Managing hybrid cloud infrastructure can require additional expertise.

3.6 Learning Resources

* Azure Official Website: https://azure.microsoft.com/
* Microsoft Azure Documentation: https://learn.microsoft.com/azure/
* Microsoft Learn: https://learn.microsoft.com/
* Azure Architecture Center: https://learn.microsoft.com/azure/architecture/

⸻

4. Google Cloud Platform (GCP)

4.1 Overview

Google Cloud Platform (GCP) is a cloud computing platform provided by Google.

It offers services for computing, storage, networking, databases, artificial intelligence, machine learning, data analytics and application deployment.

GCP allows developers and organisations to build and run applications using Google’s cloud infrastructure.

It is particularly well known for its data analytics, machine learning, Kubernetes and container-related services.

4.2 Important GCP Services

Service	Description	Purpose
Compute Engine	Provides virtual machines on Google’s infrastructure.	Running applications and workloads.
Cloud Storage	Object storage service.	Storing files, images, videos and backups.
Cloud SQL	Managed relational database service.	Managing structured application data.
BigQuery	Serverless data analytics and data warehouse platform.	Analysing large datasets.
Cloud Run	Managed platform for running containerised applications.	Deploying applications without managing servers.
Google Kubernetes Engine (GKE)	Managed Kubernetes service.	Managing containerised applications.
Cloud IAM	Identity and access management service.	Controlling access to cloud resources.
Cloud Functions	Event-driven serverless execution service.	Running code in response to events.
Cloud Monitoring	Monitoring service for cloud resources and applications.	Tracking performance and system health.
Pub/Sub	Messaging and event delivery service.	Communication between applications and services.

4.3 Practical Example

Consider an organisation that collects information from thousands of customers.

* Compute Engine can run application servers.
* Cloud Storage can store customer files and application data.
* Cloud SQL can manage structured information.
* BigQuery can analyse large amounts of collected data.
* Cloud Run can deploy containerised applications.
* GKE can manage container-based systems.
* Cloud Monitoring can track application health.

These services help organisations process data and operate applications efficiently.

4.4 Advantages of GCP

1. Data Analytics: BigQuery provides powerful large-scale data analysis capabilities.
2. Machine Learning: Google Cloud provides services and infrastructure for AI and machine learning.
3. Kubernetes Support: GKE provides managed Kubernetes capabilities.
4. Scalability: Applications can scale according to demand.
5. Infrastructure: Uses Google’s global cloud infrastructure.
6. Developer Tools: Supports modern application development and container-based deployment.

4.5 Limitations of GCP

* Some services may be unfamiliar to developers who primarily use other cloud platforms.
* Understanding cloud networking and permissions requires technical knowledge.
* Costs can increase if resources are not monitored.
* Organisations may need specialised knowledge for advanced data and AI services.

4.6 Learning Resources

* Google Cloud Official Website: https://cloud.google.com/
* Google Cloud Documentation: https://cloud.google.com/docs
* Google Cloud Skills Boost: https://www.cloudskillsboost.google/
* Google Cloud Architecture Center: https://cloud.google.com/architecture

⸻

5. Cloudflare

5.1 Overview

Cloudflare is a cloud-based platform focused on website performance, security, networking and edge computing.

It helps websites and applications become faster, more secure and more reliable.

Cloudflare provides services such as Content Delivery Network (CDN), DNS, DDoS protection, Web Application Firewall, Zero Trust security and serverless computing through Cloudflare Workers.

Unlike AWS, Azure and GCP, which provide broad cloud infrastructure services, Cloudflare is particularly focused on protecting and accelerating internet-facing applications.

It can also work alongside other cloud providers.

5.2 Important Cloudflare Services

Service	Description	Purpose
CDN	Content Delivery Network distributes website content through a network of locations.	Improving website loading speed.
DNS	Domain Name System translates domain names into IP addresses.	Helping users reach websites.
DDoS Protection	Protects against Distributed Denial of Service attacks.	Preventing malicious traffic from overwhelming websites.
WAF	Web Application Firewall filters suspicious HTTP traffic.	Protecting websites from common web attacks.
Cloudflare Workers	Serverless platform for executing code at the network edge.	Running application logic close to users.
Zero Trust / Cloudflare Access	Provides identity-based access controls.	Securing access to internal applications.
Cloudflare R2	Object storage service.	Storing files and application data.
Cloudflare Pages	Platform for hosting websites and frontend applications.	Deploying websites.
Cloudflare Tunnel	Securely connects services to Cloudflare without exposing their origin directly.	Providing secure access to private services.
Load Balancing	Distributes traffic across multiple servers or endpoints.	Improving availability and reliability.

5.3 Practical Example

Consider an organisation that operates an online website with visitors from different countries.

* CDN helps deliver website content from locations closer to visitors.
* DNS helps direct users to the correct website address.
* DDoS Protection helps protect the website from malicious traffic.
* WAF filters suspicious requests.
* Cloudflare Workers can execute application logic at the network edge.
* Cloudflare Pages can host the website.

These services improve website performance and security.

5.4 Advantages of Cloudflare

1. Performance: Helps reduce website loading times through content delivery.
2. Security: Provides DDoS protection and web application security.
3. Global Network: Operates a large distributed network.
4. Developer Tools: Provides serverless and edge computing capabilities.
5. Accessibility: Offers services that can complement existing cloud infrastructure.
6. Reliability: Supports traffic distribution and application availability.

5.5 Limitations of Cloudflare

* It does not provide the same broad range of infrastructure services as AWS, Azure and GCP.
* Advanced security and networking configurations require technical knowledge.
* Some advanced features and usage levels may require paid plans.
* It is not a complete replacement for every cloud infrastructure provider.

5.6 Learning Resources

* Cloudflare Official Website: https://www.cloudflare.com/
* Cloudflare Documentation: https://developers.cloudflare.com/
* Cloudflare Learning Center: https://www.cloudflare.com/learning/
* Cloudflare Developer Platform: https://developers.cloudflare.com/

⸻

6. Comparison of All Four Cloud Platforms

The following table compares the main characteristics of AWS, Microsoft Azure, Google Cloud Platform and Cloudflare.

Feature	AWS	Microsoft Azure	GCP	Cloudflare
Provider	Amazon	Microsoft	Google	Cloudflare
Main Focus	Broad cloud computing	Cloud computing and enterprise integration	Cloud computing, data and AI	Security, performance and edge computing
Virtual Machines	EC2	Azure Virtual Machines	Compute Engine	Not a direct equivalent
Storage	S3	Blob Storage	Cloud Storage	R2
Databases	RDS	Azure SQL	Cloud SQL	Limited database offerings compared with major cloud providers
Containers	ECS / EKS	AKS	GKE	Workers and container-related integrations
Serverless	Lambda	Azure Functions	Cloud Run / Cloud Functions	Workers
Monitoring	CloudWatch	Azure Monitor	Cloud Monitoring	Cloudflare Analytics and observability features
Security	IAM and security services	Entra ID and security services	Cloud IAM and security services	WAF, DDoS Protection and Zero Trust

6.1 Key Differences

* AWS provides a broad selection of cloud infrastructure and application services.
* Microsoft Azure is strongly integrated with Microsoft’s enterprise ecosystem.
* GCP is well known for data analytics, AI and Kubernetes-related services.
* Cloudflare focuses on website performance, security, networking and edge computing.

All four platforms have different strengths and can be used according to an organisation’s requirements.

⸻

7. Importance of Cloud Platforms in DevOps

Cloud computing plays an important role in modern DevOps practices.

DevOps combines software development and IT operations to improve collaboration, automation and software delivery.

Cloud platforms help DevOps teams build, test, deploy and monitor applications efficiently.

7.1 Infrastructure as a Service

Cloud providers allow teams to create virtual servers, networks and storage resources whenever required.

For example, AWS EC2 and Azure Virtual Machines can be used to create virtual environments for applications.

7.2 Continuous Integration and Continuous Deployment

CI/CD is a process that automates software building, testing and deployment.

Cloud platforms integrate with tools such as GitHub Actions, Azure Pipelines and AWS developer tools to automate application delivery.

7.3 Containerisation

Containers package applications and their dependencies together.

Docker is commonly used to create and run containers.

Cloud platforms provide services such as Amazon ECS, Azure AKS and Google Kubernetes Engine to run and manage containerised applications.

7.4 Monitoring and Logging

Monitoring helps DevOps engineers identify performance problems, application errors and infrastructure failures.

Examples include:

* AWS CloudWatch
* Azure Monitor
* Google Cloud Monitoring
* Cloudflare Analytics

7.5 Security and Access Management

Cloud platforms provide identity and access management services to control who can use infrastructure resources.

Examples include AWS IAM, Microsoft Entra ID and Google Cloud IAM.

These services help organisations protect their applications and data.

⸻

8. Practical Cloud Architecture Example

Consider a company that wants to deploy a web application.

A typical cloud-based application architecture may include:

1. A user accesses the website through a browser.
2. DNS directs the user to the website.
3. A CDN delivers static content efficiently.
4. A cloud server or container runs the application.
5. A database stores user and application information.
6. Storage services maintain files and backups.
7. Security services protect the application.
8. Monitoring services track performance and errors.

The same architecture can be implemented using different combinations of AWS, Azure, GCP and Cloudflare services.

Example Service Mapping

Requirement	AWS	Azure	GCP	Cloudflare
Compute	EC2	Virtual Machines	Compute Engine	Workers
File Storage	S3	Blob Storage	Cloud Storage	R2
Database	RDS	Azure SQL	Cloud SQL	Not a direct equivalent
Monitoring	CloudWatch	Azure Monitor	Cloud Monitoring	Analytics
Security	IAM and security services	Entra ID and security services	Cloud IAM and security services	WAF and DDoS Protection

⸻

9. Security and Cost Considerations

Cloud platforms provide flexible resources, but they must be configured and managed carefully.

Security Considerations

* Use strong passwords and multi-factor authentication.
* Follow the principle of least privilege when assigning permissions.
* Protect sensitive information using encryption.
* Keep software and systems updated.
* Monitor logs and security alerts.
* Avoid exposing private credentials or API keys.
* Configure network access restrictions appropriately.

Cost Considerations

Cloud services may charge based on usage, storage, computing time, network traffic or other service-specific pricing models.

To avoid unexpected expenses:

* Review the pricing information before using a service.
* Use free learning resources and documentation.
* Set budgets and billing alerts where applicable.
* Stop or delete resources when they are no longer required.
* Avoid creating unnecessary virtual machines or paid resources.

For this exploration task, no paid cloud resources were created or purchased. The work was based on platform documentation and service research.

⸻

10. Overall Findings and Conclusion

Through this cloud platform exploration, I gained an understanding of four major cloud technology platforms: AWS, Microsoft Azure, Google Cloud Platform and Cloudflare.

I learned that cloud computing allows organisations to use computing resources over the internet without maintaining all physical infrastructure themselves.

AWS provides a wide range of cloud services for computing, storage, databases, networking and DevOps.

Microsoft Azure provides cloud infrastructure with strong integration into Microsoft’s enterprise ecosystem.

Google Cloud Platform provides services for computing, storage, data analytics, artificial intelligence and container management.

Cloudflare focuses on website security, performance, networking and edge computing.

Although these platforms offer different services, all of them help organisations build, deploy, secure and manage modern applications.

This exploration improved my understanding of cloud infrastructure, virtual machines, storage, databases, networking, containers, security and monitoring.

It also helped me understand how cloud services support modern DevOps workflows and application deployment.

⸻

11. References

The following official websites and documentation resources were referred to during this exploration.

Amazon Web Services

* https://aws.amazon.com/
* https://docs.aws.amazon.com/
* https://skillbuilder.aws/

Microsoft Azure

* https://azure.microsoft.com/
* https://learn.microsoft.com/azure/
* https://learn.microsoft.com/

Google Cloud Platform

* https://cloud.google.com/
* https://cloud.google.com/docs
* https://www.cloudskillsboost.google/

Cloudflare

* https://www.cloudflare.com/
* https://developers.cloudflare.com/
* https://www.cloudflare.com/learning/

⸻

End of Report

Task: Cloud Platform Exploration
Platforms Explored: AWS, Microsoft Azure, Google Cloud Platform and Cloudflare
Submission Format: Markdown Documentation and Loom Screen Recording