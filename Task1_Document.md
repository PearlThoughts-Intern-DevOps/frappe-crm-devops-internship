  # Frappe CRM: Architecture, Workflows & DevOps Overview

   ### 1. What Frappe CRM Is & Who It Is For
    - Overview: What Frappe CRM is (open-source, lightweight CRM designed for modern sales teams).
    - Core Problem Solved: Eliminates the complexity and high cost of traditional enterprise CRMs with a fast, intuitive interface.
    - Tech Stack: Python (Frappe Framework backend), MariaDB 10.8 (database), Redis (caching & queues), and Vue 3 / Vite (frontend SPA).

   ## Explaination:
     First we will start by understanding what frappe framework is:
     It is a python framework that provides the user with some basic tasks like Database ORM & schema engine (DocTypes)- Authentication & user roles/permissions- Background job queues (Redis / RQ)- Real-time WebSockets (Socket.IO)- Bench CLI command line tool.

     What Frappe CRM is: It is an Client Relationship Manager build on top of frappe framework, SO basically it uses the builtins provided by the framework but outsource some extra adaptations in the application


   ### 2. How It Is Different (The Architectural Shift)
    - **Monolith Desk vs. Decoupled SPA**: Traditional Frappe apps (like ERPNext) render pages on the server via Jinja templates inside the legacy "Frappe Desk". Frappe CRM is completely decoupled: a modern Single Page
    Application (SPA) built with Vue 3 and Frappe UI, communicating with the backend through whitelisted REST/RPC APIs.
    - **In-Browser Form Scripting (Zero Build Step)**: Unlike typical Vue apps where changes require a rebuild, business rules and form scripts in Frappe CRM run evaluated directly in the browser using `new Function()`. Admins
    can customize forms without triggering CI/CD deployments.


   ## How Frappe CRM model proves to be better then normal CRM applications:
     Normal CRM based application uses a Server Side Rendering(SSR)-->
     Whenever the frontend sends a request to the backend the calculate the output and then renders the html file on the server itself to display the user. Which Increases the load on the server and can result into higher response latency

     This is solved by Frappe CRM by implementing a Decoupled Single Page Application where the frontend and backend are connected with just the api calls, No more rendering of the html file on the server but server just calculate the logical output of the given query and sends the output in json format to frontend where frontend doesnt render the whole page again but just changes the component which needs to be changes reducing response time and also saving the computing cost
    ---

    ---

   ### 3. Core Business Workflows
    - **Lead to Deal Pipeline**:
      - Unqualified inquiries enter as **Leads**.
      - Leads undergo automated domain enrichment (scraping company info and logos) and qualification.
      - Qualified leads smoothly convert into **Deals**, managed on visual drag-and-drop Kanban boards across stages (Discovery, Proposal, Won/Lost).
    - **Unified Activity Timeline**: All interactions—phone calls via Twilio/Exotel, notes, tasks, and comments—are linked polymorphically to records, keeping the entire sales history in one place.


    ┌──────────────┐   ┌────────────────────────┐   ┌────────────────────────┐
    │              │   │                        │   │                        │
    │ Lead Created ├──►│ Qualify["Qualification │ ┌►│ Kanban Pipeline Stages │
    │              │   │                        │ │ │                        │
    └───────┬──────┘   └────────────────────────┘ │ └────────────────────────┘
            │                                     │
            └────────┐                            │
    ┌──────────────┐ │ ┌────────────────────────┐ │ ┌────────────────────────┐
    │              │ │ │                        │ │ │                        │
    │   Qualify    │ └►│      Enrichment"]      │ │ │   Closed Won / Lost    │
    │              │   │                        │ │ │                        │
    └───────┬──────┘   └────────────────────────┘ │ └────────────────────────┘
            │                                     │              ▲            
            │                       ┌─────────────┘              │            
            │          ┌────────────────────────┐                │            
            │          │            ┴           │                │            
            └─────────►│    Convert to Deal     ├────────────────┘            
                       │                        │
                       └────────────────────────┘

    This diagram illustrates the Sales Pipeline Workflow in Frappe CRM. It maps how an initial, unverified prospective customer transforms into a
  verified revenue opportunity and progresses through to a final business outcome.

    [1. Lead Created] ──► [2. Qualification & Enrichment] ──► [3. Convert to Deal] ──► [4. Kanban Pipeline] ──► [5. Closed Won / Lost]
  ──────
  ## Step-by-Step Theoretical Breakdown

   ## 1. Lead Created (Ingestion & Entry)

  • What happens: A raw inquiry enters the CRM system.
  • How it gets created:
      • Through website contact forms (via Frappe's REST API).
      • Through incoming marketing campaigns, emails, or CSV data imports.
      • Manually entered by a sales development representative (SDR).
  • Under the Hood (tabCRM Lead): The record contains basic unverified data: person name, email, phone number, and organization website domain.
  ──────
   ### 2. Qualification & Enrichment (Intelligence & Verification)

  • What happens: Before spending sales time, the lead must be enriched with intelligence and evaluated.
  • Two key processes occur here:
      1. Automated Domain Enrichment (crm/domain_enrichment/):
          • Frappe CRM automatically detects the company's domain (e.g., acme.com).
          • A background Redis queue worker launches a web crawler using BeautifulSoup and tldextract.
          • It scrapes public company metadata, branding logos, OpenGraph tags, and social media handles (LinkedIn, X/Twitter), populating the lead
          details automatically.
      2. Lead Qualification & Scoring:
          • The sales rep contacts the lead (via built-in Twilio/Exotel WebRTC calling or WhatsApp).
          • They qualify the lead based on criteria like BANT (Budget, Authority, Need, and Timeline).


  ──────
   ### 3. Convert to Deal (The Milestone Transition)

  • What happens: Once a lead demonstrates real buying intent, it is converted into a Deal.
  • Why the separation between Lead and Deal matters:
      • A Lead is just a person or company showing interest (cost center).
      • A Deal is an active financial opportunity with an assigned monetary value, currency, and expected closing date (revenue pipeline).
  • Under the Hood:
      • Clicking "Convert to Deal" executes an automated transaction in Frappe.
      • It creates a CRM Deal record, associates or creates a Contact and CRM Organization, and carries over all historical call logs, notes, tasks,
      and email threads without losing context.

  ──────
   ### 4. Kanban Pipeline Stages (Deal Progression)

  • What happens: The sales team visually manages all active deals using a drag-and-drop Kanban Board.
  • Typical Pipeline Stages:
      1. Discovery / Prospecting: Assessing requirements.
      2. Proposal Sent: Presenting quotes, estimates, or demos.
      3. Negotiation: Finalizing contract terms and pricing.
  • Key Capabilities:
      • As sales reps drag deals between Kanban columns, stage probabilities update automatically, recalculating forecasted revenue.
      • Multi-currency support handles exchange rates automatically (crm/api/exchange_rate.py).

  ──────
   ### 5. Closed Won / Closed Lost (Final Outcome & Analytics)

  • What happens: The deal reaches its final lifecycle state:
      • Closed Won: The customer signs the contract; revenue is secured. Can be synced directly to ERPNext to generate sales invoices.
      • Closed Lost: The deal falls through. Frappe CRM triggers a modal asking for the Lost Reason (e.g., pricing, competitor, timing), feeding sales
      analytics dashboards to improve future conversion rates.

    ---

   ### 4. DevOps, Docker Setup & The Bug We Fixed
    - **Docker Architecture**: Runs 3 isolated containers via Docker Compose: `mariadb`, `redis`, and `frappe` (Bench).
    - **The Bug We Resolved**: The MariaDB 11.8 client in `frappe/bench:latest` enforced TLS/SSL by default, which failed when connecting to the non-SSL `mariadb:10.8` container, preventing site creation (`tabSingles doesn't
    exist`).
    - **The Solution**: Configured `[client] skip-ssl` in `docker/init.sh` to allow seamless local orchestration.
     ### Explanation & Theory: Docker Architecture, The SSL Bug & The Resolution
  This section explains the DevOps containerization architecture of Frappe CRM, the root cause of the MariaDB TLS error, and why our fix resolved it.
  ──────
   ## 1. Docker Architecture: The Multi-Tier Container Stack

  Frappe CRM uses a multi-tier containerized architecture orchestrated via docker-compose.yml. Each service runs in an isolated container on a private
  Docker bridge network:
    [ Client Browser: http://crm.localhost:8000 ]
                        │
                        ▼
           ┌─────────────────────────┐
           │   frappe (Bench:latest) │  <-- Port 8000 (HTTP) & Port 9000 (Socket.IO)
           │  - Web server (Gunicorn)│
           │  - RQ Background Workers│
           │  - Scheduler Daemon     │
           └────────────┬────────────┘
                        │
            ┌───────────┴───────────┐
            ▼                       ▼
    ┌──────────────┐        ┌──────────────┐
    │   mariadb    │        │    redis     │
    │ (MariaDB 10.8│        │(Redis:alpine)│
    │  Port 3306)  │        │  Port 6379)  │
    └──────────────┘        └──────────────┘

   ### What each container does:
    1. mariadb (mariadb:10.8):
        • The relational database engine storing all DocType schemas, CRM records, user accounts, and permissions.
        • Data persists across container restarts via the Docker volume mariadb-data.
    2. redis (redis:alpine):
        • High-throughput in-memory datastore.
        • Serves 3 distinct roles: Cache (web session storage), Queue (asynchronous job queues for RQ workers), and Socket.IO Pub/Sub (real-time
        notification broadcasts).
    3. frappe (frappe/bench:latest):
        • Mounts the local workspace and runs the process supervisor (init.sh).
        • Runs the Python WSGI web server, background workers, and scheduler.
    ──────
   ## 2. The Bug: Why tabSingles doesn't exist Happened

   To understand the bug, we have to look at the TLS/SSL negotiation handshake between the database client and the database server:
 
     Frappe Container (Client)                             MariaDB Container (Server)
     [MariaDB 11.8 Client]                                  [MariaDB 10.8 Server]
              │                                                      │
              │─── 1. Connect (Require SSL = TRUE) ─────────────────►│
              │                                                      │
              │◄── 2. Error: "Server does not support SSL" ──────────│
              │                                                      │
     [Process Aborted: ERROR 2026]
     [Database created, but 0 tables imported]
              │
              ▼
     [bench start runs anyway]
              │
              ▼
      [Scheduler queries 'tabSingles'] ──► CRASH: Table Doesn't Exist!
   ### The Root Cause Breakdown: 
    1. Client-Server Version Mismatch:
        • The base image frappe/bench:latest was recently updated with MariaDB 11.8 client libraries.
        • Starting in MariaDB 11+, client utilities (mysql, mariadb) enforce SSL  encryption by default (ssl=TRUE).
    2. The Non-SSL Database Container:
        • The database service in docker-compose.yml runs mariadb:10.8 inside an  internal Docker network, without TLS certificates configured.
    3. The Aborted Schema Migration:
        • When init.sh ran bench new-site crm.localhost, bench invoked the mariadb  CLI to load the initial database schema (240 tables including
        tabSingles, tabDocType, etc.).
        • The CLI aborted with: ERROR 2026 (HY000): TLS/SSL error: SSL is required,  but the server does not support it.
    4. The Downstream Crash:
        • Because init.sh lacked set -e, the script did not stop. It launched the  web and scheduler processes on an empty database.
        • When the scheduler executed its first query (SELECT value FROM tabSingles WHERE doctype='System Settings'), MariaDB threw:
        pymysql.err.ProgrammingError: (1146, "Table '_c8b3e5206096f0bd.tabSingles' doesn't exist").

  ──────
   ## 3. The Solution: How We Fixed It
    The fix addresses both client configuration and script reliability:

    1. Client Configuration ([client] skip-ssl):
    By writing echo -e "[client]\nskip-ssl" > ~/.my.cnf, we instruct the MariaDB 11.8 client not to demand TLS when connecting over the private,
    internal Docker bridge network.
    2. Defensive Shell Scripting (set -e):git
    Adding set -e at the top of init.sh ensures that if any command fails in the future, the script halts immediately rather than booting up a corrupted
    instance.
    3. Deprecation Cleanup (--mariadb-user-host-login-scope='%'):
    Replaces the deprecated --no-mariadb-socket flag with the official Frappe 15 login scope option.
    ──────
