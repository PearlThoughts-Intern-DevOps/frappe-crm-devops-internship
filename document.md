# Frappe CRM: Architecture, Workflows & DevOps Exploration

**Author:** Abhishek G M  
**GitHub Username:** AbhishekGM23  
**Repository:** [frappe-crm-devops-internship](https://github.com/PearlThoughts-Intern-DevOps/frappe-crm-devops-internship)  
**Branch:** `task1-AbhishekGM23`  

---

## 1. Executive Summary & Overview

### What Frappe CRM Is
Frappe CRM is a modern, open-source Customer Relationship Management application crafted specifically for modern sales and revenue operations teams. Built atop the robust Python-based Frappe Framework, Frappe CRM eliminates the user interface complexity, vendor lock-in, and aggressive per-seat pricing models typical of legacy enterprise CRMs (such as Salesforce and HubSpot).

### Core Problem Solved
Traditional enterprise CRMs often suffer from:
1. **Bloated & Rigid Interfaces:** Requiring lengthy onboarding, slow page reloads, and cumbersome form navigation.
2. **Expensive Per-Seat Licensing:** Restricting company-wide access to sales data.
3. **Complex Customization Cycles:** Demanding full application rebuilds and redeployments for simple form alterations or business logic updates.

Frappe CRM addresses these bottlenecks through:
- **Unlimited Users & Open Source Freedom:** Transparent data ownership without artificial user tiers.
- **Decoupled Single Page Application (SPA):** Instant page transitions, reactive client-side rendering, and responsive keyboard navigation.
- **Dynamic In-Browser Customization:** Live form scripting and schema adjustments without code recompilation.
- **Full Omnichannel Sales Workflow:** Consolidated Lead-to-Deal pipelines, visual drag-and-drop Kanban boards, and integrated communications (telephony, WhatsApp, email).

---

## 2. Architectural Paradigm Shift: Legacy Frappe Desk vs. Decoupled Vue 3 SPA

To truly understand Frappe CRM, one must examine how it differs from traditional Frappe applications (such as ERPNext):

```
+-----------------------------------------------------------------------------------------+
|                               Traditional Frappe App (SSR)                              |
|                                                                                         |
|  [Browser]  <==== HTML/Jinja + Desk Bundle =====  [Gunicorn / Frappe Desk Monolith]     |
|             (Full page or desk-wrapper reload)    (Server renders HTML & Desk UI)       |
+-----------------------------------------------------------------------------------------+

+-----------------------------------------------------------------------------------------+
|                                  Frappe CRM (Decoupled SPA)                             |
|                                                                                         |
|  [Vue 3 SPA] <==== Pure JSON RPC/REST (Whitelisted APIs) ====> [Frappe Backend Engine]  |
|  (Frappe UI, Pinia,                                             (DocType ORM, MariaDB,  |
|   Vite, Tailwind)                                                Redis, RQ Workers)     |
+-----------------------------------------------------------------------------------------+
```

### Key Architectural Differences:
1. **Server-Side Rendering (SSR) vs. Client-Side Rendering (CSR):**
   - Standard Frappe apps rely on "Frappe Desk," which renders Jinja templates and monolithic desk JavaScript on the server.
   - Frappe CRM decouples the frontend entirely: it serves a Vue 3 Single Page Application bundled with Vite, interacting with the Python backend purely through typed JSON endpoints (`frappe.call` / REST).
2. **In-Browser Form Scripting (Zero Build Step):**
   - In standard frontend development, custom business logic requires compiling new code via npm/yarn.
   - Frappe CRM introduces `crm_form_script`, allowing administrators to write custom JavaScript logic directly in the CRM UI. The frontend evaluates these scripts at runtime using JavaScript function constructors (`new Function()`), enabling live form validation, dynamic field triggers, and computation without triggering a CI/CD build or server restart.
3. **Optimized Network Footprint:**
   - Instead of transmitting server-rendered HTML blocks, only minimal JSON payloads travel across the wire, minimizing latency and drastically reducing server CPU load.

---

## 3. Technology Stack Breakdown

| Layer | Technologies | Purpose |
| :--- | :--- | :--- |
| **Frontend Framework** | Vue 3 (Composition API), Vite 8 | Reactive user interface, component lifecycle, instant HMR during development |
| **UI Component Library** | Frappe UI, Headless UI, Tailwind CSS | Accessible, responsive, customizable design system |
| **State & Routing** | Pinia, Vue Router 4 | Centralized client state management and SPA navigation |
| **Specialized UI Engines**| Vue Flow, TipTap, Leaflet, CropperJS | Interactive workflow diagrams, rich-text note editor, geospatial mapping |
| **Backend Framework** | Frappe Framework v15 (Python 3.10+) | Application framework, metadata ORM, authentication, role-based access |
| **Database** | MariaDB 10.8 (InnoDB, UTF8mb4) | Relational persistence, transactional integrity, dynamic DocType table schemas |
| **In-Memory Datastore** | Redis (Alpine) | Tri-role storage: Session Cache, RQ Background Task Queue, Real-time Pub/Sub |
| **Real-time Push** | Socket.IO Client & Server | Live notification delivery, instant comment updates, multi-user presence |
| **Telephony Integration** | Twilio Voice SDK, Exotel API | In-browser VoIP calling, call recording, mobile forwarding |
| **Quality & CI/CD** | Vitest, Playwright, ESLint, GitHub Actions | Unit tests, end-to-end browser tests, automated linting and docker builds |

---

## 4. Repository & Codebase Directory Deep Dive

```
frappe-crm-devops-internship/
├── .devcontainer/         # VS Code containerized dev environment definitions
├── .github/
│   └── workflows/         # GitHub Actions CI/CD automation pipelines
├── crm/                   # Core Frappe Backend Application (Python)
│   ├── api/               # Whitelisted RPC/REST API controller endpoints
│   ├── automation/        # Event-driven automation flow engine and triggers
│   ├── fcrm/doctype/      # Core CRM DocType definitions (Schemas, Controllers, JSON)
│   ├── integrations/      # Telephony (Twilio/Exotel), WhatsApp, and ERPNext connectors
│   ├── lead_syncing/      # External lead ingestion and sync workers
│   ├── permissions/       # Sales organizational hierarchy and permission handlers
│   ├── overrides/         # Overridden Frappe standard doctypes (Contact, Email Template)
│   ├── hooks.py           # Frappe application registry, event hooks, and route mappings
│   └── install.py         # App installation, fixtures setup, and default seeding
├── docker/                # Containerization setup
│   ├── docker-compose.yml # Multi-container orchestration (frappe, mariadb, redis)
│   └── init.sh            # Container bootstrap, bench initialization, and site installer
├── docs/                  # Application documentation
├── e2e/                   # Playwright end-to-end test suite
├── frappe-ui/             # Vendored Frappe UI component library
├── frontend/              # Modern Vue 3 SPA frontend source
│   ├── src/
│   │   ├── components/    # Reusable UI widgets, activity timelines, form fields
│   │   ├── pages/         # Top-level views (Leads, Deals, Contacts, Tasks, Dashboard)
│   │   ├── stores/        # Pinia reactive state stores
│   │   ├── router.js      # Client-side route declarations
│   │   └── socket.js      # Real-time WebSocket connection listener
│   ├── package.json       # Node dependencies and build scripts
│   └── vite.config.js     # Vite bundler configuration and proxy rules
└── pyproject.toml         # Python build metadata and linting specifications
```

### In-Depth Directory Highlights:
- **`crm/fcrm/doctype/`**: Houses all business entities. Crucial DocTypes include:
  - `crm_lead`: Inbound prospects with qualification status, temperature, and score.
  - `crm_deal`: Active pipeline deals with value, stage, probability, and expected close date.
  - `crm_call_log`: Telephony logs capturing caller ID, duration, status, and recording URL.
  - `crm_form_script`: Repository of custom JavaScript code snippets executed in user browsers.
  - `crm_sales_hierarchy`: Structural organization of sales reps, managers, and approval hierarchies.
- **`crm/hooks.py`**: The nervous system of the Frappe app. Connects custom methods to document lifecycle events (`before_insert`, `validate`, `on_update`), binds scheduled background jobs via cron, and maps `/crm/*` URL requests to the frontend entrypoint.
- **`frontend/src/pages/`**: Contains dedicated desktop and mobile views (`Deal.vue`, `MobileDeal.vue`, `Leads.vue`, `Dashboard.vue`), ensuring seamless responsive usability across devices.

---

## 5. Core Business Workflows

### 1. Lead-to-Deal Conversion Lifecycle

```
[Inbound Inquiry / Web Form]
             │
             ▼
      [CRM Lead Created]
             │
             ├──► [Automated Domain Enrichment] (Fetches company metadata & logo)
             ├──► [Lead Scoring & Temperature] (Cold / Warm / Hot)
             │
             ▼
    [Qualification Gate]
             │
     ┌───────┴───────┐
     ▼               ▼
[Disqualified]  [Qualified]
                     │
                     ▼
             [Convert to Deal] ──► Auto-creates/links Contact & Organization
                     │
                     ▼
         [Kanban Pipeline Stages]
         (Discovery ➔ Demo ➔ Proposal ➔ Negotiation)
                     │
             ┌───────┴───────┐
             ▼               ▼
        [Won (100%)]    [Lost (Reason Logged)]
             │
             ▼ (Optional)
     [ERPNext Customer & Quotation Sync]
```

### 2. Unified Polymorphic Activity Timeline
In modern sales, context fragmentation loses deals. Frappe CRM solves this with a unified polymorphic stream:
- Calls made via Twilio or Exotel are automatically recorded and linked directly to the parent Lead or Deal.
- Emails exchanged with the client thread directly into the record view.
- Tasks, notes, and comments appear chronologically, ensuring any team member has full visibility into client history.

### 3. Event-Driven Automation Engine
Located in `crm/automation/`, this engine enables sales operations to design triggers without writing code:
- **Triggers:** `prospect_message_received`, `lead_qualified`, `deal_stage_changed`, `task_overdue`.
- **Actions:** `AdjustLeadScore`, `SetLeadTemperature`, `SendCRMNotification`, `ConvertLeadToDeal`.

---

## 6. DevOps Architecture & Troubleshooting Deep Dive

### Container Topology & Infrastructure

The application runs locally in an isolated Docker network composed of three dedicated containers:

```
                  [ Client Browser ]
             http://localhost:8000/crm
                         │
                         ▼
           ┌───────────────────────────┐
           │   frappe (Bench:latest)   │  Port 8000 (HTTP / Gunicorn)
           │  - Bench CLI & Environment│  Port 9000 (Socket.IO Real-time)
           │  - RQ Background Workers  │
           │  - Python WSGI Server     │
           └─────────────┬─────────────┘
                         │ Docker Network (crm_default)
            ┌────────────┴────────────┐
            ▼                         ▼
   ┌─────────────────┐       ┌─────────────────┐
   │     mariadb     │       │      redis      │
   │  (MariaDB 10.8) │       │  (Redis:alpine) │
   │    Port 3306    │       │    Port 6379    │
   │ [mariadb-data]  │       └─────────────────┘
   └─────────────────┘
```

### Critical DevOps Challenges & Solutions

During the initial deployment of Frappe CRM on a local machine, three significant technical hurdles were diagnosed and resolved:

#### 1. Windows Line Endings (CRLF vs. LF) in `init.sh`
- **Symptom:** The Frappe container crashed immediately upon startup with errors:
  ```
  /workspace/init.sh: line 2: $'\r': command not found
  /workspace/init.sh: line 41: syntax error: unexpected end of file
  ```
- **Root Cause:** Git on Windows default checkout settings (`core.autocrlf = true`) converted Unix line terminators (`LF`) to Windows format (`CRLF`). When mounted into the Linux-based `frappe/bench` container, the carriage returns (`\r`) broke bash parsing.
- **Resolution:** Stripped carriage returns from `docker/init.sh` converting file terminators to clean Unix `LF`.

#### 2. MariaDB 11.8 Client vs. MariaDB 10.8 Server TLS Handshake Bug (ERROR 2026)
- **Symptom:** When `bench new-site crm.localhost` attempted to create database tables, the operation aborted with:
  ```
  ERROR 2026 (HY000): TLS/SSL error: SSL is required, but the server does not support it
  ```
  If allowed to continue, the web server crashed downstream with `pymysql.err.ProgrammingError: (1146, "Table '...tabSingles' doesn't exist")` because zero tables were imported.
- **Root Cause:** The upstream base image `frappe/bench:latest` was updated with the MariaDB 11.8 client toolset, which enforces TLS by default (`ssl=TRUE`). However, the `mariadb:10.8` container on the internal Docker network does not have SSL certificates configured.
- **Resolution:** Injected a client configuration into the user profile inside the container:
  ```bash
  echo -e "[client]\nskip-ssl" > /home/frappe/.my.cnf
  ```
  This instructed the MariaDB client to connect over plain TCP on the internal Docker bridge network, allowing all 240+ Frappe DocType tables to import cleanly.

#### 3. Windows Subdomain Resolution & Multi-Tenant Routing
- **Observation:** `crm.localhost` does not resolve automatically through Windows OS DNS commands (`ping` or `curl`) without elevated hosts file modification.
- **Resolution:** Frappe handles site selection via `sites/currentsite.txt` generated by `bench use crm.localhost`. When a user navigates to `http://localhost:8000/crm` or `http://127.0.0.1:8000/crm`, the Frappe WSGI server automatically matches the request to `crm.localhost`. Additionally, Chromium-based browsers (Chrome, Edge) natively resolve all `*.localhost` subdomains to `127.0.0.1` at the browser layer.

---

## 7. Local Execution & Verification

### Running Frappe CRM Locally:
```bash
# 1. Navigate to the docker directory
cd docker

# 2. Ensure init.sh has Unix LF line endings
# 3. Start the containers in detached mode
docker compose up -d

# 4. Access the CRM application in your web browser
# URL: http://localhost:8000/crm  or  http://crm.localhost:8000/crm
# Default Credentials:
#   Username: Administrator
#   Password: admin
```

---

## 8. Loom Video Presentation Script (Camera ON)

Use this script as a speaking guide for the 3–5 minute Loom demonstration:

### [00:00 - 00:45] Introduction & Task Goal
> "Hello everyone! My name is Abhishek G M, and this is my presentation for Task 1 of the DevOps Internship. Today, I explored Frappe CRM—an open-source, affordable, and flexible CRM tailored for sales teams. In this video, I will walk you through what the project is, its architectural design, how I set it up locally using Docker, and the DevOps obstacles encountered and resolved."

### [00:45 - 01:45] Architectural Overview & Tech Stack
> "Frappe CRM represents a modern architectural shift away from the legacy Frappe Desk. Instead of server-rendered HTML via Jinja, Frappe CRM features a fully decoupled Single Page Application built on Vue 3, Frappe UI, Pinia, and Vite.
> On the backend, it utilizes Frappe Framework v15 with MariaDB for relational storage, Redis for session caching, RQ job queues, and Socket.IO for real-time notifications. A standout feature is in-browser form scripting, allowing zero-build-step customizations directly through the UI."

### [01:45 - 03:00] Live Demonstration of Locally Running Application
> *(Switch screen share to your browser displaying http://localhost:8000/crm)*  
> "Here you can see Frappe CRM running live on my local workstation at `http://localhost:8000/crm`.  
> As you can see, we have the complete CRM workspace:
> 1. **Leads Page:** Inbound prospects with status badges and lead qualification tools.
> 2. **Deals Kanban Board:** A drag-and-drop visual pipeline tracking deals from discovery to close.
> 3. **Unified Activity Timeline:** Calls, tasks, notes, and emails consolidated in a single view.
> 4. **Settings & Integrations:** Built-in connectors for Twilio VoIP, Exotel telephony, WhatsApp, and ERPNext."

### [03:00 - 04:15] DevOps Engineering & Key Troubleshooting
> *(Switch screen share to terminal or docker desktop)*  
> "From a DevOps perspective, the application runs on a 3-tier container architecture: `frappe` (application server), `mariadb` (database), and `redis` (cache and queues).
> During deployment on Windows, I identified and resolved two critical issues:
> First, Windows CRLF line endings in `init.sh` caused bash execution failure inside the Linux container, resolved by normalizing line endings to LF.
> Second, a TLS handshake mismatch where MariaDB client 11.8 in `frappe/bench:latest` enforced SSL against MariaDB 10.8 server, throwing ERROR 2026. This was resolved by configuring `skip-ssl` in `/home/frappe/.my.cnf`."

### [04:15 - 04:45] Conclusion & PR Submission
> "To conclude, Task 1 allowed me to thoroughly explore the architecture, business logic, and deployment workflows of Frappe CRM without modifying application source code. I have pushed my documentation to branch `task1-AbhishekGM23` and raised the pull request. Thank you!"

---

## 9. Conclusion
Frappe CRM demonstrates the power of pairing an established, mature metadata backend (Frappe Framework) with a high-performance, modern reactive frontend (Vue 3 / Frappe UI). The containerized Docker setup provides a reproducible, isolated local environment that is production-ready for automated CI/CD deployment pipelines.
