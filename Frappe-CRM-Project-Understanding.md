# Frappe CRM – Project Understanding and Exploration

# 1. Project Overview

Frappe CRM is an open-source Customer Relationship Management (CRM) application developed using the Frappe ecosystem.

Customer Relationship Management is a process that helps organizations manage their interactions with existing customers and potential customers.

A CRM application helps businesses organize customer information, track sales opportunities, manage communication and improve customer relationships.

Frappe CRM provides functionality to manage customer-related activities, including:

- Leads and prospects.
- Contacts and organizations.
- Deals and sales opportunities.
- Tasks and follow-ups.
- Customer-related information and activities.

# 2. Technology Stack

Frappe CRM belongs to the Frappe ecosystem. The following technologies are relevant to understanding its architecture.

| Python | Backend programming language |
| Frappe Framework | Backend web application framework |
| JavaScript | Frontend and application scripting |
| Vue.js | Frontend framework used in the Frappe UI ecosystem |
| MariaDB | Relational database used in typical Frappe deployments |
| Redis | Caching and background-job infrastructure |
| Node.js | JavaScript runtime and frontend tooling |
| Yarn | JavaScript package management, where configured |
| Docker | Containerization |
| Docker Compose | Management of multiple application services |
| Git | Version control |
| GitHub | Source-code hosting and collaboration |

# 3. Components

**1. Frontend**

The frontend provides the user interface through which users interact with the CRM application.

It handles:
- Displaying application pages.
- User interactions.
- Forms and data entry.
- Communication with backend APIs.

**2. Backend**

The Frappe Framework provides backend application functionality.

It handles:
- Business logic.
- API requests.
- Authentication and authorization.
- Data processing.
- Communication with the database.

**3. Database**

MariaDB is commonly used in Frappe deployments as the relational database.

It stores application information such as:
- Customer details.
- Leads.
- Contacts.
- Deals.
- User and application data.

**4. Redis**

Redis is commonly used in Frappe deployments for:
- Caching.
- Background job queues.
- Supporting asynchronous processing.

**5. Web Server and Application Services**

Depending on the deployment configuration, additional services may handle HTTP requests, application serving and background processing.

The actual services used by this repository should be identified from its Docker Compose files.

**Dockerfile**

Defines how the development environment image is built.

**Docker Compose configuration**

Can define multiple services required for the development environment.

The actual files present inside this repository's `.devcontainer` directory should be inspected to understand its implementation.

