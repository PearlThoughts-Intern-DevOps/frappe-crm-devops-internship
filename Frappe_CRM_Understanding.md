# Task 1: Exploring Frappe CRM

Repository: `PearlThoughts-Intern-DevOps/frappe-crm-devops-internship`
No application code was changed. This task was only to explore and run the project.

## 1. What is Frappe CRM?

Frappe CRM is an open-source CRM (Customer Relationship Management) tool for sales teams. It helps a team track:

- **Leads**: people or companies that might buy.
- **Deals**: qualified leads that are being worked toward a sale.
- **Contacts and Organizations**: the people and companies behind them.
- **Activities**: notes, tasks, comments, emails and calls on each lead or deal.

Main features: an all-in-one Lead/Deal page, a drag-and-drop Kanban board, custom saved views, and integrations with Twilio, Exotel (calls), WhatsApp and ERPNext.

## 2. Technologies used

| Area | Technology |
|---|---|
| Backend framework | **Frappe Framework** (Python) |
| Database | **MariaDB** |
| Cache, job queue | **Redis** |
| Frontend | **Vue 3**, **frappe-ui** component library, **Tailwind CSS** |
| Frontend build | **Vite** |
| Realtime updates | **socket.io** |
| Testing | **Vitest** (frontend), **Playwright** (end to end), Frappe test runner (backend) |
| Code quality | ruff, ESLint, oxlint, Prettier, pre-commit |
| CI/CD | **GitHub Actions** (`.github/workflows/`) |
| Containers | **Docker** and docker-compose |

## 3. How the application works

Frappe CRM is a **Frappe app** (a Python package that plugs into the Frappe framework) with a **Vue 3 single-page app** on top.

Flow: Browser (Vue app) -> API calls to `/api/method/crm.api...` -> Frappe + CRM Python code -> MariaDB. Redis handles cache and background jobs, and socket.io pushes live updates to the browser.

How the page loads: the route `/crm` is defined in `crm/hooks.py` and served by `crm/www/crm.py`, which checks that the user is logged in and sends startup data to the Vue app. The Vue app is built with Vite into `crm/public/frontend`.

Running parts: a web server (port 8000), a socket.io server (port 9000), a worker for background jobs, a scheduler for timed jobs, MariaDB and Redis.

## 4. Project folders

| Folder | What it contains |
|---|---|
| `crm/` | The Frappe app (Python backend) |
| `crm/fcrm/doctype/` | 40 DocTypes, which are the data models (Lead, Deal, Organization, Task and so on) |
| `crm/api/` | API methods the frontend calls |
| `crm/hooks.py` | Connects the app to Frappe: routes, events, permissions, scheduled jobs |
| `crm/integrations/` | Twilio, Exotel and ERPNext integrations |
| `frontend/` | The Vue 3 app (`src/pages`, `src/components`, `src/stores`) |
| `docker/` | `docker-compose.yml` and `init.sh` for local setup |
| `.github/workflows/` | CI pipelines: linting, tests, migration test, image builds |
| `e2e/` | Playwright end-to-end tests |
| `docs/` | User documentation |

## 5. How I ran it locally

I used **Docker Compose** on Windows. It starts three containers: MariaDB, Redis and the Frappe bench. The setup script (`init.sh`) creates the bench, installs the CRM app, creates the site `crm.localhost` and starts the servers. The first setup took about 15 to 20 minutes. I opened `http://crm.localhost:8000/login`, signed in as `Administrator` / `admin`, and used the CRM at `/crm`.

Problems I solved:

1. **Docker engine crash.** The C: drive was full. I freed space and reset Docker Desktop's WSL 2 data.
2. **Port 8000 in use.** Another container used it. I found it with `docker ps` and stopped it.
3. **DNS failure inside the container.** I added DNS servers (8.8.8.8, 1.1.1.1) to the Frappe service.
4. **`init.sh` line endings.** Windows (CRLF) line endings broke the script, so I used a copy with Linux (LF) endings.
5. **SSL error when creating the site.** The database client required SSL, but MariaDB 10.8 does not offer it. I added `skip-ssl` to the client config at the start of `init.sh`.

## 6. Key learnings for DevOps

- The app has several parts (web, realtime, worker, scheduler, MariaDB, Redis), so deployment and monitoring must cover all of them.
- Docker Compose describes the whole environment in files, so anyone can recreate it with one command.
- GitHub Actions builds container images and runs linting, unit tests, end-to-end tests and migration tests.
- The Docker setup installs CRM from the upstream Frappe repository, not from this internship repository.
- Default passwords (`admin`, DB root `123`) are for development only.