# Frappe CRM – Project Overview

## 1. Introduction

Frappe CRM is an open-source Customer Relationship Management (CRM) application designed for modern sales teams.

It helps businesses manage customer relationships, track leads and deals, organize sales activities, and maintain customer-related information in one place.

The application is built using the Frappe Framework and provides an interface for managing sales workflows.

## 2. Key Features

The major features of Frappe CRM include:

- **Lead and Deal Management:** Manage leads and deals from a centralized interface.
- **Kanban View:** Visualize and track sales activities through a Kanban board.
- **Custom Views:** Organize and display CRM information using customized views.
- **Activity Tracking:** Maintain notes, tasks, comments and activity records.
- **Communication Integrations:** Support integrations with communication platforms.
- **Business Integrations:** Connect with other business applications.

## 3. Integrations

According to the project README, Frappe CRM supports integrations with:

- Twilio
- Exotel
- WhatsApp
- ERPNext

These integrations help connect CRM activities with communication and business workflows.

## 4. Technologies Used

### Frappe Framework

Frappe Framework is the full-stack web application framework used to build Frappe CRM. It provides the foundation for application development and functionality.

### Frappe UI

Frappe UI is a Vue-based UI component library used to build the application's frontend interface.

### Docker

Docker provides a containerized environment for running the application and its supporting services.

### MariaDB

MariaDB is used as the database service in the provided Docker configuration.

### Redis

Redis is included as a supporting service in the Docker configuration.

### Yarn

Yarn is used to install frontend dependencies.

## 5. Application Architecture

Frappe CRM follows a framework-based application architecture.

The main components include:

- **Frontend:** User interface built using Frappe UI and Vue-based components.
- **Backend:** Application functionality provided through the Frappe Framework.
- **Database:** MariaDB service for storing application data.
- **Supporting Services:** Redis for supporting application operations.
- **Containerization:** Docker Compose coordinates the application and supporting services.

### High-Level Architecture

```text
             User / Browser
                   |
                   v
            Frappe CRM UI
                   |
                   v
           Frappe Framework
                   |
          -------------------
          |                 |
          v                 v
       MariaDB            Redis
          |
          v
     Application Data
```

*Note: This is a simplified conceptual representation of the components, not a detailed runtime or request-flow diagram.*

## 6. Project Setup Using Docker

The project README provides instructions for running Frappe CRM locally using Docker.

The general setup process is:

1. Install Docker and Docker Compose.
2. Download the Docker Compose configuration file.
3. Download the initialization script (`init.sh`).
4. Start the application using:

```bash
docker compose up -d
```

5. Access the application through:

```text
http://crm.localhost:8000/crm
```

### Default Login Credentials

| Field | Value |
|---|---|
| Username | Administrator |
| Password | admin |

*These are the default credentials specified in the README's Docker setup instructions.*

## 7. Development and Version Compatibility

The README describes the following compatibility:

| CRM Branch | Frappe Framework Compatibility | Status |
|---|---|---|
| main (v1.x) | Frappe v15.x and v16.x | Stable |
| develop (future v2.x) | Frappe develop / future v17 | Unstable |

The README also provides a development setup using Frappe Bench, including commands to initialize a bench, retrieve the CRM application and create a site.

Frontend development uses Yarn and Vite.

## 8. Understanding the Project from a DevOps Perspective

From a DevOps perspective, this project provides an opportunity to understand:

- Running a multi-service application using Docker Compose.
- Understanding containerized application environments.
- Identifying application dependencies and supporting services.
- Understanding how frontend and backend components work together.
- Managing application configuration.
- Observing application startup and initialization through container logs.
- Accessing a locally deployed web application.

## 9. Conclusion

Frappe CRM is an open-source CRM application built on the Frappe Framework, with a Vue-based frontend powered by Frappe UI.

Exploring this project provides an understanding of its application architecture, technologies, integrations, dependencies and Docker-based deployment approach.

The project serves as a practical learning opportunity for understanding how a multi-service web application can be organized and run in a containerized environment.

## References

- Frappe CRM GitHub Repository: https://github.com/frappe/crm
- Frappe CRM README: https://github.com/frappe/crm/blob/develop/README.md
- Frappe Framework Documentation: https://docs.frappe.io/framework
- Frappe Bench Documentation: https://docs.frappe.io/framework/user/en/bench
