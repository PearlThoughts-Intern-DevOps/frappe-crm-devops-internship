# Task 1 – Frappe CRM Project Exploration

**Repository:** PearlThoughts-Intern-DevOps/frappe-crm-devops-internship  
**Candidate:** Gamjt19  
**Branch:** `task1-Gamjt19`  
**Task:** Explore and understand the Frappe CRM project

## 1. Project Overview

Frappe CRM is an open-source Customer Relationship Management application designed to help sales teams manage leads, deals, contacts, organizations, and sales activities.

It provides a centralized interface for tracking customer interactions and monitoring sales progress.

The application includes features such as:

- Lead and deal management
- Contacts and organizations
- Kanban and list views
- Sales dashboards and reports
- Tasks and communication logs
- Integrations with communication services
- Custom views and automation capabilities

## 2. Technologies Used

| Technology | Purpose |
|---|---|
| Python | Backend application logic |
| Frappe Framework | Backend framework, database operations, APIs, permissions, and DocTypes |
| Vue.js 3 | Frontend user interface |
| JavaScript | Frontend application logic |
| Frappe UI | Frontend components and communication with Frappe |
| MariaDB | Relational database |
| Redis | Caching and background job infrastructure |
| Node.js | Frontend development and asset building |
| Vite | Frontend development server and build tool |
| Docker | Containerized local environment |
| Docker Compose | Running the application services together |
| Playwright | End-to-end browser testing |
| Vitest | Frontend unit testing |

## 3. Project Structure

The repository contains the following important directories:

| Directory | Purpose |
|---|---|
| `crm/` | Main Python backend application |
| `crm/api/` | Backend API modules |
| `crm/fcrm/` | CRM DocTypes and business logic |
| `crm/integrations/` | External service integrations |
| `crm/automation/` | CRM automation functionality |
| `frontend/` | Vue.js frontend application |
| `frontend/src/` | Frontend pages, components, stores, and routing |
| `frappe-ui/` | Frappe UI frontend library and packages |
| `docker/` | Docker Compose and initialization configuration |
| `docs/` | Project documentation |
| `e2e/` | End-to-end tests |
| `scripts/` | Supporting scripts |
| `.github/` | GitHub workflows and repository configuration |

## 4. Application Architecture

Frappe CRM follows a frontend-backend architecture built around the Frappe Framework.

### Frontend

The frontend is developed using Vue.js 3 and Frappe UI.

Important frontend areas include:

- `frontend/src/pages/` – Application pages such as Leads and Deals.
- `frontend/src/components/` – Reusable UI components.
- `frontend/src/stores/` – State and data management.
- `frontend/src/router.js` – Frontend route configuration.
- `frontend/src/App.vue` – Main application component.

### Backend

The backend is developed using Python and the Frappe Framework.

Important backend areas include:

- `crm/api/` – API functionality.
- `crm/fcrm/doctype/` – CRM DocTypes and their business logic.
- `crm/hooks.py` – Application hooks, permissions, events, scheduled tasks, and integrations.

### Database and supporting services

- MariaDB stores application data.
- Redis supports caching and background processing.
- Frappe Bench manages the application environment and runs the development server.

### Conceptual request flow

1. A user interacts with the Vue.js frontend.
2. The frontend requests data or performs an operation through Frappe UI resources and Frappe APIs.
3. The Python backend processes the request using Frappe Framework and CRM business logic.
4. Data is read from or written to MariaDB.
5. The response is returned to the frontend and displayed to the user.

This describes the general architecture observed during project exploration.

## 5. Local Development Environment

I used Windows 11 with WSL2 Ubuntu and Docker Desktop to run the application locally.

The repository's Docker configuration starts three main services:

| Container | Image | Responsibility |
|---|---|---|
| `crm-frappe-1` | `frappe/bench:latest` | Frappe Bench and CRM application |
| `crm-mariadb-1` | `mariadb:10.8` | Database |
| `crm-redis-1` | `redis:alpine` | Cache and queue support |

The Docker Compose configuration exposes:

- Port `8000` – Frappe web application
- Port `9000` – Additional development service port

### Commands used

Clone the repository:

```bash
git clone https://github.com/PearlThoughts-Intern-DevOps/frappe-crm-devops-internship.git
```

Navigate to the Docker directory:

```bash
cd frappe-crm-devops-internship/docker
```

Start the services:

```bash
docker compose up -d
```

Check running containers:

```bash
docker compose ps
```

View application logs:

```bash
docker compose logs -f frappe
```

The application is accessible locally at:

`http://localhost:8000`

The CRM route is:

`http://crm.localhost:8000/crm`

## 6. CRM Features Explored

### Dashboard

The dashboard provides an overview of sales activity through metrics and visualizations, including:

- Total Leads
- Average time to close a lead
- Ongoing Deals
- Won Deals
- Average Won Deal Value
- Average Deal Value
- Sales Trend
- Forecasted Revenue

The dashboard also provides date and sales-user filters. Since this was a fresh local installation, the metrics initially displayed zero values.

### Leads

The Leads section provides a view for managing potential customers.

The list view includes fields such as:

- Full Name
- Email
- Organization
- Status
- Source

The interface provides filtering, sorting, column customization, creation, and import options.

### Other CRM modules

The application navigation also provides modules for managing sales-related records and activities, including Deals, Contacts, Organizations, Tasks, and Call Logs.

## 7. Backend Code Exploration – Lead Management

I explored the following files to understand how lead management is implemented:

- `crm/fcrm/doctype/crm_lead/crm_lead.py`
- `crm/fcrm/doctype/crm_lead/crm_lead.json`
- `crm/api/dashboard.py`
- `crm/hooks.py`

The `CRMLead` Python controller contains business logic for lead creation and validation.

Some of the operations observed include:

- Setting the full name and lead title.
- Validating email addresses and unique fields.
- Assigning default lead status.
- Managing lead ownership and sharing.
- Handling lost reasons.
- Applying service-level agreement (SLA) logic.
- Triggering website-based lead enrichment after insertion.

The DocType JSON file defines the lead data structure, including fields, field types, naming series, and list-view configuration.

The dashboard API contains methods for retrieving sales metrics and dashboard information.

## 8. Docker and Initialization Process

The `docker/docker-compose.yml` file defines the services required for local development.

The `docker/init.sh` script automates the initial setup.

The initialization process includes:

1. Creating a Frappe Bench environment.
2. Configuring MariaDB and Redis connections.
3. Downloading the CRM application.
4. Creating the `crm.localhost` site.
5. Installing the CRM application.
6. Enabling development-related settings.
7. Starting the Bench development server.

This helped me understand how Docker Compose coordinates the application, database, and supporting services.

## 9. Challenges and Troubleshooting

During local setup, I encountered the following issues:

### Docker command unavailable in WSL

Initially, Docker commands were unavailable inside Ubuntu.

**Resolution:** Enabled WSL integration for the Ubuntu distribution through Docker Desktop settings.

### MariaDB TLS/SSL connection issue

During site creation, the MariaDB client attempted to use SSL, but the MariaDB server did not have SSL enabled.

**Resolution:** Configured the MariaDB client inside the running Frappe container to skip SSL for this local development environment, allowing the database connection to succeed.

### Application startup

After completing initialization and resolving the database connection issue, I verified that the containers were running and successfully accessed the CRM login page and dashboard.

## 10. Key Learnings

Through this exploration, I gained an understanding of:

- How a Frappe-based application is structured.
- How Vue.js and Frappe UI are used for the frontend.
- How Python and Frappe Framework handle backend logic.
- How DocTypes define application data models.
- How MariaDB and Redis support the application.
- How Docker Compose manages multiple services.
- How initialization scripts automate environment setup.
- How frontend and backend components work together in a CRM application.

## 11. Conclusion

I successfully cloned the Frappe CRM repository, configured the local environment using Docker Compose, completed the initialization process, and accessed the application locally.

I explored the repository structure, important backend and frontend files, Docker configuration, and major CRM modules.

This task helped me understand the overall architecture and the technologies involved in running and developing a Frappe-based CRM application.

**Note:** This submission documents project exploration and local setup. No application source-code changes were made.
