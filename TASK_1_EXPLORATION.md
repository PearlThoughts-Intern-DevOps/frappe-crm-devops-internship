# Task 1: Frappe CRM Exploration & Architecture Report

**Author:** Gourob Das ([@gourobdas0103](https://github.com/gourobdas0103))  
**Role:** DevOps Engineering Intern  
**Organization:** PearlThoughts  
**Repository:** `PearlThoughts-Intern-DevOps/frappe-crm-devops-internship`  
**Branch:** `task1-gourobdas0103`  
**Submission Date:** November 2026  

---

## 1. Executive Summary

This report documents the architectural exploration, codebase decomposition, and local containerized deployment of **Frappe CRM**, executed as part of **Task 1: Explore Frappe CRM** in the PearlThoughts DevOps Internship Program.

Frappe CRM is an enterprise-ready, open-source Customer Relationship Management application designed for high-velocity modern sales organizations. Unlike monolithic, proprietary CRMs that impose steep per-seat licenses and rigid schema constraints, Frappe CRM offers an unopinionated, extensible, metadata-driven architecture. It combines the declarative backend capabilities of the **Frappe Framework (v15)** with a responsive, reactive Single-Page Application (SPA) frontend powered by **Vue 3**, **Vite**, and **Tailwind CSS**.

The primary objectives accomplished in this exploration include:
1. **Containerized Stack Initialization**: Deploying the multi-service Frappe CRM stack locally using Docker and Docker Compose.
2. **Architectural Analysis**: Deconstructing the 3-tier decoupled architecture, including request lifecycles, database interactions, and real-time push events.
3. **Directory Structure & Codebase Navigation**: Mapping out backend apps (`crm/`), frontend SPA (`frontend/`), reusable component libraries (`frappe-ui/`), and DevOps orchestration scripts (`docker/`).
4. **Core Business Modules & DocTypes**: Investigating data models for Leads, Deals, Contacts, Organizations, and the omni-channel activity timeline.
5. **DevOps Engineering Insights**: Addressing cross-platform compatibility issues (CRLF line endings, database SSL negotiations, and multi-tenancy port routing).
6. **Automated Quality Gates**: Analyzing GitHub Actions workflows enforcing linting, unit testing, and Playwright end-to-end coverage.

---

## 2. High-Level System Architecture

Frappe CRM is architected on a modern decoupled topology consisting of three distinct operational tiers:

1. **Client Tier (Presentation Layer)**: A Vue 3 SPA loaded into the client browser, handling client-side routing, optimistic UI updates, drag-and-drop Kanban state, and real-time WebSocket communication.
2. **Application Tier (Business Logic Layer)**: The Frappe Bench runtime executing Python 3.10+, Gunicorn/Werkzeug HTTP servers, Celery-like asynchronous background workers, periodic scheduled cron jobs, and a Node.js Socket.IO event broadcaster.
3. **Data Tier (Persistence & In-Memory Layer)**: An ACID-compliant MariaDB relational database managing schema and record transactions, paired with Redis instances fulfilling caching, job queues, and WebSocket pub/sub channels.

```mermaid
flowchart TD
    subgraph ClientLayer["Client Layer (Browser)"]
        Browser["User Browser\n(Vue 3 SPA at http://localhost:8000/crm)"]
    end

    subgraph ContainerNetwork["Docker Compose Network (crm)"]
        subgraph AppService["Frappe Bench Container (crm-frappe-1)"]
            WebServer["Werkzeug / Gunicorn Web Server\n(Port 8000)"]
            SocketIO["Socket.IO Server\n(Port 9000 - Real-time Events)"]
            Scheduler["Bench Scheduler\n(Periodic Background Tasks)"]
            Worker["Background Queue Worker\n(Async Task Execution)"]
            AppLogic["Frappe Framework v15 + CRM App\n(/apps/crm & /apps/frappe)"]
        end

        subgraph DBService["Database Container (crm-mariadb-1)"]
            MariaDB["MariaDB 10.8\n(Port 3306 - utf8mb4)\nTransactional Schema & DocTypes"]
        end

        subgraph CacheService["Cache & Message Broker (crm-redis-1)"]
            Redis["Redis Alpine (Port 6379)\nIn-Memory Cache | Job Queues | Pub/Sub"]
        end
    end

    subgraph ExternalIntegrations["External Telephony & Cloud Services"]
        Twilio["Twilio Voice SDK / Calling API"]
        Exotel["Exotel Telephony Service"]
        WhatsApp["WhatsApp Business Gateway"]
        ERPNext["ERPNext ERP Sync"]
    end

    Browser -->|HTTP REST APIs / RPC| WebServer
    Browser -->|WebSocket Bidirectional Push| SocketIO
    WebServer --> AppLogic
    Scheduler --> AppLogic
    Worker --> AppLogic
    AppLogic -->|PyMySQL Queries (utf8mb4)| MariaDB
    AppLogic -->|Key-Value Caching & Queuing| Redis
    SocketIO -->|Pub/Sub Event Sync| Redis
    AppLogic -.->|Voice Calls & SMS Webhooks| Twilio
    AppLogic -.->|Agent Mobile Dialing| Exotel
    AppLogic -.->|Direct Messaging| WhatsApp
    AppLogic -.->|Accounting & Invoice Sync| ERPNext
```

---

## 3. Technology Stack Breakdown

| Technology | Category | Role in Frappe CRM |
| :--- | :--- | :--- |
| **Python (3.10+)** | Backend Language | Core application logic, DocType controller classes, REST API routes, and data validation. |
| **Frappe Framework (v15)** | Full-Stack Framework | Declarative ORM, metadata engine, Role-Based Access Control (RBAC), authentication, migrations, and Desk administration. |
| **Vue.js 3** | Frontend UI Framework | Powers the Single Page Application using the Composition API, reactive state management, and lifecycle hooks. |
| **Vite** | Frontend Build Tool | Lightning-fast development server with Hot Module Replacement (HMR) and optimized production Rollup/esbuild bundling. |
| **Tailwind CSS** | Styling System | Utility-first styling framework providing responsive layout design, consistent design tokens, and dark mode support. |
| **Frappe UI** | Component Library | Vendored UI primitives customized for Frappe applications (buttons, modals, dropdowns, data tables, form layouts). |
| **Pinia / Vue Router** | State & Navigation | Reactive client-side stores for Leads, Deals, Users, Notifications, and client-side view switching without page reloads. |
| **MariaDB (10.8)** | Relational Database | Persistent database engine utilizing `utf8mb4` encoding to store dynamic DocType tables, indexes, and transactional audit trails. |
| **Redis** | In-Memory Data Store | High-throughput distributed caching, background task queues (default, short, long), and real-time Socket.IO pub/sub. |
| **Node.js Socket.IO** | Real-Time Engine | Pushes live activity updates, notifications, and record locks to connected browser sessions instantly. |
| **Playwright** | E2E Testing | Automated end-to-end browser testing validating critical UI flows across Chromium, Firefox, and WebKit. |
| **Vitest** | Frontend Testing | Fast unit test runner verifying frontend utility functions, data transformers, and reactive stores. |
| **Ruff / ESLint / Prettier** | Code Quality | Automated linters and formatters enforcing strict Python PEP-8 and JavaScript/Vue style consistency. |
| **Docker & Docker Compose** | Infrastructure & DevOps | Multi-container orchestration providing reproducible local development and production environments. |

---

## 4. Repository Directory Structure

```text
frappe-crm-devops-internship/
├── .devcontainer/              # VS Code Remote Container development specifications
├── .github/
│   └── workflows/              # GitHub Actions CI/CD automation pipelines
│       ├── linters.yml         # Python (Ruff) and JavaScript (ESLint/Prettier) checks
│       ├── builds.yml          # Frontend asset compilation verification
│       ├── server-tests.yml    # Backend unit and integration test runner
│       ├── frontend-tests.yml  # Vitest test suite for Vue 3 modules
│       ├── ui-tests.yml        # Playwright browser end-to-end automation
│       └── migration-test.yml  # Database migration compatibility testing
├── .pi/                        # Project context, API contracts, architectural specs (PLAN, SPEC, ARCHIVE)
├── crm/                        # Frappe Backend Application (Python)
│   ├── api/                    # Custom REST API endpoints and RPC controllers
│   ├── automation/             # Workflow triggers, automated actions, and field updates
│   ├── fcrm/
│   │   └── doctype/            # Core CRM DocTypes (crm_lead, crm_deal, crm_task, crm_call_log, etc.)
│   ├── integrations/           # Third-party adapters (Twilio, Exotel, WhatsApp, ERPNext)
│   ├── patches/                # Database migration patches executed during bench migrate
│   ├── public/                 # Static backend assets and built frontend production bundles
│   └── hooks.py                # Frappe application lifecycle hooks, event subscriptions, and cron tasks
├── docker/                     # Docker Compose deployment files
│   ├── docker-compose.yml      # Multi-container service definitions (MariaDB, Redis, Frappe Bench)
│   └── init.sh                 # Environment initialization and bootstrap script
├── docs/                       # Project documentation, guides, and user hierarchy maps
├── e2e/                        # End-to-end test scenarios and Playwright configurations
├── frappe-ui/                  # Vendored Vue 3 design system and UI components
├── frontend/                   # Vue 3 SPA source code
│   ├── src/
│   │   ├── components/         # Reusable widgets (Kanban board, Activity timeline, Telephony modal)
│   │   ├── pages/              # Primary route views (Leads.vue, Deals.vue, Contacts.vue, Dashboard.vue)
│   │   ├── stores/             # Centralized Pinia reactive state stores
│   │   ├── utils/              # Data parsing, field transform helpers, and scripting evaluators
│   │   ├── router.js           # Client-side routing definitions
│   │   └── App.vue             # Root application component mounting global modals
│   ├── package.json            # Node.js dependencies, scripts, and build targets
│   └── vite.config.js          # Vite build orchestration and proxy configuration
├── scripts/                    # Supporting operational and setup shell scripts
├── pyproject.toml              # Python packaging standards, metadata, and dependencies
└── README.md                   # Main project overview and getting started guide
```

---

## 5. Core Business Modules & Data Models (DocTypes)

Frappe CRM centers its functionality on custom metadata-driven models called **DocTypes**. Each DocType dynamically provisions an underlying MariaDB table (prefixed with `tab`) along with JSON metadata and Python controller hooks:

1. **Leads (`crm_lead`)**:
   - Represents unvetted prospects captured through inbound marketing, webhooks, or manual entry.
   - Tracks lead origin (Website, Email, Campaign, Referral), qualification status, assigned sales agent, and response time SLAs.
   - Provides a one-click automated conversion mechanism into structured Deals, Organizations, and Contacts.

2. **Deals (`crm_deal`)**:
   - Encapsulates active qualified sales opportunities moving across a stage-gate pipeline.
   - Configurable stages: *Qualification* $\rightarrow$ *Meeting Scheduled* $\rightarrow$ *Proposal Sent* $\rightarrow$ *Negotiation* $\rightarrow$ *Closed Won* / *Closed Lost*.
   - Attributes include monetary opportunity value, currency, estimated closure date, winning probability percentage, and deal loss rationale.
   - In the frontend, deals are visualized through an interactive, drag-and-drop **Kanban Board** that executes optimistic UI updates and synchronizes state with the backend via REST API.

3. **Organizations (`crm_organization`) & Contacts (`crm_contacts`)**:
   - Maintains account-level intelligence and individual stakeholder profiles.
   - Enables bi-directional linking: one organization links to multiple decision-makers, tracking email addresses, direct dial numbers, LinkedIn handles, and billing details.

4. **Activities & Telephony (`crm_call_log`, `fcrm_note`, `crm_task`)**:
   - Powers the unified **Activity Timeline** attached to every Lead and Deal.
   - Supports integrated VoIP telephony via Twilio and Exotel: users can initiate outbound calls, receive incoming calls, record audio conversations, and append timestamps automatically.
   - Tracks follow-up reminders, task completion dates, and rich-text meeting notes using the embedded TipTap editor.

5. **Dynamic Form Scripting Engine**:
   - Located under `frontend/src/data/script.js` and `frontend/src/data/document.js`.
   - Allows administrators to customize form behavior dynamically (field dependencies, cascading dropdowns, computed calculations, and custom action dialogs) evaluated safely in the browser without rebuilding frontend assets.

---

## 6. Request Lifecycle & Data Flow

When a user performs an action (e.g., updating a deal stage on the Kanban board):

1. **User Interaction**: The sales representative drags a deal card to the *Proposal Sent* column.
2. **Reactive Store Dispatch**: The Pinia store (`frontend/src/stores/deal.js`) updates the local reactive state optimistically to deliver zero-latency feedback.
3. **API Request**: The Frappe UI resource layer sends an asynchronous HTTP `POST` request to `/api/method/frappe.client.set_value` or custom REST endpoints.
4. **Authentication & Authorization**: The Frappe Framework interceptor authenticates the user session (Cookie/Token) and validates Role-Based Permissions against the `crm_deal` DocType rules.
5. **Business Validation & Lifecycle Hooks**: The backend controller (`crm/fcrm/doctype/crm_deal/crm_deal.py`) executes validation hooks:
   - `validate()`: Verifies that required fields are populated and business logic constraints hold.
   - `on_update()`: Triggers automated workflows, SLA timers, and notifications.
6. **Database Persistence**: The changes are committed to `tabcrm_deal` in MariaDB with transactional consistency (`COMMIT`).
7. **Cache & Real-Time Sync**: Caches in Redis are updated, and a WebSocket event is published through Redis to Socket.IO, broadcasting the updated record state to all active team members simultaneously.

---

## 7. Local Deployment & DevOps Engineering Insights

### 7.1 Containerized Setup Procedure
The stack is orchestrated using `docker/docker-compose.yml`, which defines three interdependent services:
- **`crm-mariadb-1`**: Runs `mariadb:10.8` initialized with `utf8mb4` character set, collation `utf8mb4_unicode_ci`, and a named persistent volume `crm_mariadb-data`.
- **`crm-redis-1`**: Runs `redis:alpine` providing low-latency in-memory data structures for caching and background message queues.
- **`crm-frappe-1`**: Runs `frappe/bench:latest`, exposing ports `8000:8000` (Web UI/API) and `9000:9000` (Socket.IO).

To launch the environment:
```powershell
# Navigate to the docker directory and launch services in detached mode
cd docker
docker compose up -d

# Follow the container bootstrapping logs
docker logs -f crm-frappe-1
```

### 7.2 DevOps Challenges Encountered & Resolved

During the local deployment on Windows host environments, two critical engineering challenges were identified and addressed:

1. **Windows CRLF vs. Linux Bash Compatibility**:
   - **Problem**: When the repository is cloned on Windows with `core.autocrlf = true`, the startup script `docker/init.sh` is written with Windows carriage return characters (`\r\n`). When mounted into the Linux container (`frappe/bench`), bash threw execution errors: `/workspace/init.sh: line 2: $'\r': command not found` and syntax errors causing the container to exit prematurely.
   - **DevOps Solution**: Converted `docker/init.sh` line endings to standard Linux line feeds (`\n` LF) and ensured proper encoding prior to launching the container.

2. **MariaDB Client TLS Requirement**:
   - **Problem**: Recent updates to Debian-based MariaDB client packages enforce TLS encryption by default. Over internal Docker networks without TLS certificates, database operations can trigger `ERROR 2026 (HY000): TLS/SSL error: SSL is required, but the server does not support it`.
   - **DevOps Solution**: Setting `[client] ssl = 0` inside `/home/frappe/.my.cnf` enables secure, direct unencrypted internal container-to-container socket communication over the isolated Docker network bridge.

---

## 8. Continuous Integration & Quality Assurance

The repository maintains an automated CI/CD pipeline implemented via GitHub Actions:

- **`linters.yml`**: Runs code quality audits on pull requests using **Ruff** for high-speed Python linting and **ESLint / Prettier** for frontend formatting compliance.
- **`builds.yml`**: Executes `vite build` to guarantee that TypeScript/Vue bundle compilation succeeds without chunking errors.
- **`server-tests.yml`**: Spins up temporary MariaDB and Redis containers, provisions a test site, and executes automated Python test suites against DocType controllers.
- **`frontend-tests.yml`**: Runs **Vitest** for frontend utility functions, expression evaluators, and document reactive proxies.
- **`ui-tests.yml`**: Launches headless browser instances via **Playwright** to execute comprehensive end-to-end tests across Leads, Deals, and Activity logs.

---

## 9. Conclusion & Deliverables

Frappe CRM demonstrates an effective software engineering architecture that unites the rapid prototyping power of a Python metadata engine with the interactivity and responsiveness of a modern Vue 3 SPA. The platform is robust, modular, and optimized for containerized cloud deployment.

### Submission Artifacts:
- **Repository Branch**: [`task1-gourobdas0103`](https://github.com/PearlThoughts-Intern-DevOps/frappe-crm-devops-internship/tree/task1-gourobdas0103)
- **Exploration Report**: [`TASK_1_EXPLORATION.md`](file:///C:/Users/goura/Desktop/frappe-crm-devops-internship/TASK_1_EXPLORATION.md)
- **Local Application URL**: `http://localhost:8000/crm` (Admin: `Administrator` / Password: `admin`)
