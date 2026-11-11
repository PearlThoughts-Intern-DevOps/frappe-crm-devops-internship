# Task 1: Frappe CRM Project Exploration

**Internship:** PearlThoughts DevOps Internship  
**Project:** Frappe CRM  
**Internship repository:** [PearlThoughts-Intern-DevOps/frappe-crm-devops-internship](https://github.com/PearlThoughts-Intern-DevOps/frappe-crm-devops-internship)  
**Application source:** [frappe/crm](https://github.com/frappe/crm)  
**Task branch:** `task1-Shirisha-Thakur`

## 1. Project Overview

[Frappe CRM](https://github.com/frappe/crm) is an open-source Customer Relationship Management application built on the Frappe Framework. It helps sales teams manage customer information and sales activities, including leads, contacts, organizations and deals.

The objective of this task was to explore the application and its source structure, understand its technology stack and service architecture, run the application locally, and document the findings.

## 2. Application Technology Stack

The following technologies are used by the **Frappe CRM application itself**. They are taken from the Frappe CRM source repository and its frontend dependency configuration. They are not the tools used on the local Windows machine.

### Frontend

| Technology | Purpose in Frappe CRM |
|---|---|
| **Vue.js 3** | Frontend JavaScript framework used to build the interactive CRM interface. |
| **JavaScript / TypeScript** | Languages used for frontend application behaviour and typed code. |
| **Frappe UI** | Vue-based component library used to build the user interface. |
| **Vue Router** | Handles navigation between frontend pages and views. |
| **Pinia** | Manages shared frontend application state. |
| **Tailwind CSS** | Utility-first CSS framework used for frontend styling. |
| **Vite** | Frontend development server and build tool. |

### Backend

| Technology | Purpose in Frappe CRM |
|---|---|
| **Python** | Main language used for server-side application logic. |
| **Frappe Framework** | Backend web framework providing the application structure, DocTypes, ORM, permissions and API functionality. |
| **Frappe CRM** | The CRM application package that implements customer and sales-related functionality on top of the Frappe Framework. |

### Database and Supporting Services

| Technology / Service | Purpose |
|---|---|
| **MariaDB** | Relational database used by the local environment to store site and CRM records. |
| **Redis** | Supporting service used by the Frappe environment for caching and queued/background work. |
| **Socket.IO** | Supports real-time communication features between the application and connected clients. |

## 3. High-Level Application Architecture

```text
                 USER
                  |
                  v
          WEB BROWSER / UI
       Vue 3 + Frappe UI
       Vue Router + Pinia
       Tailwind CSS
                  |
             HTTP / API
                  |
                  v
          FRAPPE BACKEND
        Python + Frappe Framework
          Frappe CRM logic
                  |
          +-------+-------+
          |               |
          v               v
       DATABASE       SUPPORTING SERVICE
       MariaDB             Redis
     CRM records       Cache / queues

          Socket.IO supports
          real-time communication

     Docker Compose runs the
     configured local services
```

### Request flow

1. A user opens Frappe CRM in a web browser and interacts with the Vue-based frontend.
2. The frontend sends requests to the Frappe backend.
3. The Python-based Frappe Framework processes the request and applies the CRM application logic.
4. The backend reads or updates application records in MariaDB.
5. Redis supports configured caching and background-job functions.
6. The response is returned to the frontend for display. Socket.IO supports real-time communication where required.

## 4. Main CRM Areas

| CRM area | Purpose |
|---|---|
| **Leads** | Keeps records of prospective customers and initial sales interest. |
| **Contacts** | Stores information about individual people. |
| **Organizations** | Stores company and organization information. |
| **Deals** | Tracks potential sales opportunities and their progress. |

### Basic CRM workflow

A typical CRM process connects prospective customers, people, organizations and sales opportunities:

1. Capture a lead.
2. Review the prospect and identify the next action.
3. Maintain the relevant contact details.
4. Associate the contact or opportunity with an organization where applicable.
5. Track the deal as it progresses.
6. Record follow-ups and next steps.

## 5. Local Environment Explored

The internship repository's Docker configuration was used to run the application locally.

| Component | Role in the local environment |
|---|---|
| `crm-frappe-1` | Runs the Frappe application and Bench environment. |
| `crm-mariadb-1` | Provides the MariaDB database service. |
| `crm-redis-1` | Provides the Redis supporting service. |
| `docker/docker-compose.yml` | Defines the local Docker services and their configuration. |
| `docker/init.sh` | Initialization script used by the local environment. |

**Verified local application URL:** `http://crm-task1.localhost:8000`

### Relevant repository paths

| Path | Description |
|---|---|
| `docker/` | Docker-related configuration for the local environment. |
| `docker/docker-compose.yml` | Docker Compose service definitions and configuration. |
| `docker/init.sh` | Environment initialization script. |
| `docker/recovery-backup/` | Recovery/backup-related resources created during troubleshooting. |

## 6. Database and Site Initialization Findings

A Frappe site has its own configuration and associated database. Successful site initialization creates the database schema and required tables.

| Site / database | Finding |
|---|---|
| Original site: `crm.localhost` | Referenced database `_c8b3e5206096f0bd`. |
| Original database | Found to contain zero tables. |
| New site: `crm-task1.localhost` | Created as a separate initialized site. |
| New database: `_3dfa23c5af3c2958` | Verified to contain 291 tables. |

The application was verified at `http://crm-task1.localhost:8000` after the Frappe container was restarted. Passwords and other credentials are intentionally excluded from this documentation.

## 7. Troubleshooting Summary

| Issue | Investigation | Outcome |
|---|---|---|
| MariaDB client SSL connection error | The server reported `have_ssl=DISABLED` and `require_secure_transport=OFF`. A client connection using `--skip-ssl` succeeded. | A temporary client-side `skip-ssl` configuration was used inside the running Frappe container for local testing. |
| Original site database had no tables | Database `_c8b3e5206096f0bd` existed but contained zero tables. | A separate site and database were initialized; the new database contained 291 tables. |
| Browser reported missing `tabSingles` table | The request was still being handled against the old or incomplete site database. | Restarting `crm-frappe-1` allowed the application to load using the initialized site. |
| Scheduler disabled message | Installation output displayed `*** Scheduler is disabled ***`. | It did not prevent the application from loading in this local environment. |

**Local SSL workaround:** The `skip-ssl` client configuration was only a development workaround for the observed local client/server mismatch. It is not a production security recommendation. Production database connections should use correctly configured TLS. A configuration written only inside a running container may also be lost if that container is recreated.

## 8. Key Learnings

- Frappe CRM uses a Vue-based frontend and a Python backend built on the Frappe Framework.
- Frappe UI provides reusable Vue components for the frontend.
- The frontend communicates with the backend through application APIs.
- MariaDB stores persistent site and CRM data in the local environment.
- Redis provides supporting services such as caching and background-job queues.
- Docker Compose coordinates the application and supporting containers.
- A site directory or database can exist even when database initialization has not completed successfully.
- Checking database tables and container logs helps diagnose initialization and runtime problems.
- Changes made only inside a running container may not persist after the container is recreated.

## 9. References

| Resource | Link |
|---|---|
| Frappe CRM source repository | https://github.com/frappe/crm |
| Frappe CRM README and documented technology overview | https://github.com/frappe/crm#readme |
| Frappe CRM frontend dependency configuration | https://github.com/frappe/crm/blob/develop/frontend/package.json |
| Frappe Framework | https://github.com/frappe/frappe |
| Frappe UI | https://github.com/frappe/frappe-ui |
| Internship repository | https://github.com/PearlThoughts-Intern-DevOps/frappe-crm-devops-internship |

---

**Task 1:** Frappe CRM Project Exploration  
**Local verification:** `http://crm-task1.localhost:8000`
