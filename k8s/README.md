# Frappe CRM on Kubernetes

> Production-ready declarative Kubernetes manifests and architecture documentation for deploying Frappe CRM on Minikube and cloud clusters.

---

## At a Glance

| Component | Technology | Role |
| :--- | :--- | :--- |
| **Frontend & UI** | Vue 3 + Vite | Decoupled Single Page Application |
| **API Server** | Gunicorn (Python WSGI) | Frappe Framework v15 REST/RPC backend |
| **Reverse Proxy** | NGINX 1.25 Alpine | Static asset delivery, WebSocket & API proxy |
| **Database** | MariaDB 10.6 LTS | Relational storage with `utf8mb4` encoding |
| **Cache & Queues**| Redis 7 Alpine | Dedicated cache, job queue & WebSocket broker |
| **Real-time** | Node.js Socket.IO | Live desktop notifications and event push |
| **Background** | Python RQ | Asynchronous queue worker & singleton scheduler |

---

## System Architecture

```text
┌────────────────────────────────────────────────────────────────────────────────────────┐
│                                  CLIENT TRAFFIC LAYER                                  │
│                                                                                        │
│   Browser Request (http://crm.localhost)                                               │
│             │                                                                          │
│             ▼                                                                          │
│   ┌──────────────────────────────────┐        Fallback Direct Access                   │
│   │   Ingress Controller (Port 80)   │ ────────────────────────────────────────┐       │
│   │        (crm.localhost)           │                                         │       │
│   └─────────────────┬────────────────┘                                         │       │
└─────────────────────┼──────────────────────────────────────────────────────────┼───────┘
                      │ (ClusterIP / Port 80)                                    ▼
                      │                                        ┌─────────────────────────┐
                      │                                        │  frappe-web-svc         │
                      │                                        │  (NodePort: 30080)      │
                      │                                        └────────────┬────────────┘
                      ▼                                                     │
┌───────────────────────────────────────────────────────────────────────────┼────────────┐
│ KUBERNETES APPLICATION WORKLOADS                                          │            │
│                                                                           │            │
│   ┌──────────────────────── frappe-web Pod (Dual-Container) ──────────────┼────────┐   │
│   │                                                                       ▼        │   │
│   │   ┌────────────────────────────────────────────────────────────────────────┐   │   │
│   │   │                     Container 1: NGINX (Port 8080)                     │   │   │
│   │   │   • Serves /assets & /files directly from volume                       │   │   │
│   │   │   • Proxies dynamic / to Gunicorn                                      │   │   │
│   │   │   • Proxies /socket.io to Socket.IO service                            │   │   │
│   │   └───────────────────┬────────────────────────────────┬───────────────────┘   │   │
│   │                       │ (127.0.0.1:8000)               │ (proxy /socket.io)    │   │
│   │                       ▼                                │                       │   │
│   │   ┌────────────────────────────────────────┐           │                       │   │
│   │   │  Container 2: Gunicorn WSGI (Port 8000)│           │                       │   │
│   │   │  (Python backend / REST API)           │           │                       │   │
│   │   └───────────────────┬────────────────────┘           │                       │   │
│   └───────────────────────┼────────────────────────────────┼───────────────────────┘   │
│                           │                                │                           │
│                           │                                ▼                           │
│   ┌───────────────────────┼────────┐          ┌────────────────────────────┐           │
│   │ Asynchronous Workers  │        │          │ Real-Time WebSocket Engine │           │
│   │                       ▼        │          │                            │           │
│   │  ┌──────────────────────────┐  │          │  ┌───────────────────────┐ │           │
│   │  │ frappe-worker Pod        │  │          │  │ frappe-socketio Pod   │ │           │
│   │  │ (RQ Worker: default/long)│  │          │  │ (Node.js Port 9000)   │ │           │
│   │  └──────────────────────────┘  │          │  └───────────┬───────────┘ │           │
│   │  ┌──────────────────────────┐  │          └──────────────┼─────────────┘           │
│   │  │ frappe-scheduler Pod     │  │                         │                         │
│   │  │ (Singleton Cron Engine)  │  │                         │                         │
│   │  └──────────────────────────┘  │                         │                         │
│   │  ┌──────────────────────────┐  │                         │                         │
│   │  │ frappe-site-init (Job)   │  │                         │                         │
│   │  │ (Idempotent DB Setup)    │  │                         │                         │
│   │  └──────────────────────────┘  │                         │                         │
│   └───────────────────────┬────────┘                         │                         │
└───────────────────────────┼──────────────────────────────────┼─────────────────────────┘
                            │                                  │
                            ▼                                  ▼
┌────────────────────────────────────────────────────────────────────────────────────────┐
│ STATEFUL BACKING SERVICES & BROKERS                                                    │
│                                                                                        │
│   ┌───────────────────┐    ┌────────────────────┐    ┌─────────────────────────────┐   │
│   │ MariaDB 10.6 LTS  │    │ Redis Cache        │    │ Redis Queue                 │   │
│   │ (mariadb-svc:3306)│    │ (Port 6379)        │    │ (Port 6379)                 │   │
│   │ [utf8mb4 encoding]│    │ [Ephemeral cache]  │    │ [Background task queues]    │   │
│   └─────────┬─────────┘    └────────────────────┘    └─────────────────────────────┘   │
│             │                                                                          │
│             │              ┌───────────────────────────────────────────────────────┐   │
│             │              │ Redis Socket.IO (Port 6379)                           │   │
│             │              │ [Pub/Sub event broker for real-time WebSockets]       │◄──┘   │
│             │              └───────────────────────────────────────────────────────┘       │
└─────────────┼──────────────────────────────────────────────────────────────────────────┘
              │
              ▼
┌────────────────────────────────────────────────────────────────────────────────────────┐
│ PERSISTENT STORAGE LAYER                                                               │
│                                                                                        │
│   ┌────────────────────────────────────────┐   ┌───────────────────────────────────┐   │
│   │ mariadb-data-pvc (5Gi - RWO)           │   │ frappe-sites-pvc (10Gi - RWX)     │   │
│   │ Mount: /var/lib/mysql                  │   │ Mount: .../frappe-bench/sites     │   │
│   │ Retains SQL databases and tables       │   │ Shared assets, sites & site configs│   │
│   └────────────────────────────────────────┘   └───────────────────────────────────┘   │
└────────────────────────────────────────────────────────────────────────────────────────┘
```

---

## How It Works

### 1. Dual-Container Web Pod
- **Gunicorn** serves dynamic Python API requests on `127.0.0.1:8000`.
- **NGINX** sits in front on port `8080`, directly serving compiled CSS/JS and uploaded files from the shared volume.
- **Why this matters**: Gunicorn is a WSGI server, not a static file server. Having NGINX handle `/assets` eliminates 404 errors and keeps Python workers free for business logic.

### 2. Real-Time WebSockets
- Background tasks and desk updates push messages to `redis-socketio`.
- The `frappe-socketio` Node.js pod subscribes to these channels and broadcasts live updates to users over WebSockets.

### 3. Asynchronous Workers & Scheduler
- **RQ Workers** pull time-consuming tasks (email sync, lead enrichment) from `redis-queue` so user requests stay fast.
- **Scheduler** runs with `strategy: { type: Recreate }` to guarantee only one scheduler instance is active at a time, preventing duplicate cron jobs.

### 4. Dynamic Pod IP Database Access
- In Kubernetes, pods receive dynamic IP addresses whenever they restart.
- Our site initialization job automatically grants wildcard host access (`'user'@'%'`), ensuring web and worker pods can always connect to MariaDB without access-denied errors.

---

## Manifest Reference

```
k8s/
├── 00-namespace.yaml          # Workload isolation
├── 01-configmap.yaml          # App, MariaDB, and NGINX configs
├── 02-secret.yaml             # Encrypted credentials & keys
├── 03-storage.yaml            # Persistent volume claims
├── 04-mariadb.yaml            # MariaDB 10.6 StatefulSet & Service
├── 05-redis.yaml              # Cache, Queue, and SocketIO Redis instances
├── 06-frappe-init-job.yaml    # One-time site setup & migration job
├── 07-frappe-web.yaml         # Dual-container web pod + NodePort service
├── 08-frappe-socketio.yaml    # Node.js WebSocket service
├── 09-frappe-worker.yaml      # Asynchronous RQ background workers
├── 10-frappe-scheduler.yaml   # Singleton cron job dispatcher
├── 11-ingress.yaml            # HTTP routing for crm.localhost
└── kustomization.yaml         # Declarative index for Kustomize
```

---

### Tier-by-Tier Breakdown

#### ⚙️ Foundation & Security
* [00-namespace.yaml](./00-namespace.yaml) — Creates the `frappe-crm` namespace to keep workloads cleanly separated from system pods.
* [01-configmap.yaml](./01-configmap.yaml) — Stores non-sensitive settings: database host, Redis connection strings, `utf8mb4` MariaDB parameters, and the complete NGINX reverse-proxy configuration.
* [02-secret.yaml](./02-secret.yaml) — Securely stores MariaDB root/user passwords and the Frappe Administrator secret key.

#### 💾 Storage Layer
* [03-storage.yaml](./03-storage.yaml) — Declares two PersistentVolumeClaims:
  * `mariadb-data-pvc` (5Gi, `ReadWriteOnce`): Dedicated storage for database files.
  * `frappe-sites-pvc` (10Gi, `ReadWriteMany`): Shared volume mounted simultaneously by web, worker, and init pods.

#### 🗄️ Database & In-Memory Brokers
* [04-mariadb.yaml](./04-mariadb.yaml) — Deploys MariaDB 10.6 LTS with persistent volume mounts, safe `subPath` config loading, and authenticated health checks via `mariadb-admin ping`.
* [05-redis.yaml](./05-redis.yaml) — Deploys three isolated Redis instances with lightweight resource footprints (64MB RAM each):
  * `redis-cache`: High-speed ephemeral data caching.
  * `redis-queue`: Task queue for asynchronous jobs.
  * `redis-socketio`: Pub/Sub message broker for WebSockets.

#### 🚀 Site Initialization
* [06-frappe-init-job.yaml](./06-frappe-init-job.yaml) — Runs an idempotent setup Job before the application starts:
  1. Polls MariaDB and Redis until TCP connections are accepted (`wait-for-infra`).
  2. Seeds physical asset files into the shared volume with symlink dereferencing (`cp -rL`).
  3. Provisions the new site, installs the CRM application, and grants wildcard host access (`'user'@'%'`).

#### 🌐 Web Tier & Real-Time Engine
* [07-frappe-web.yaml](./07-frappe-web.yaml) — The primary user-facing pod combining NGINX (port 8080) and Gunicorn (port 8000). Exposed externally via `frappe-web-svc` on NodePort `30080`.
* [08-frappe-socketio.yaml](./08-frappe-socketio.yaml) — Dedicated Node.js WebSocket engine handling live real-time collaboration.

#### ⚡ Background Processing
* [09-frappe-worker.yaml](./09-frappe-worker.yaml) — Background workers consuming from `short`, `default`, and `long` task queues.
* [10-frappe-scheduler.yaml](./10-frappe-scheduler.yaml) — Cron scheduler running with `strategy: { type: Recreate }` to prevent overlapping runs.

#### 🚪 Ingress & Deployment Orchestration
* [11-ingress.yaml](./11-ingress.yaml) — Configures HTTP routing for `crm.localhost` via the Ingress Controller.
* [kustomization.yaml](./kustomization.yaml) — Resource manifest enabling single-command deployment with `kubectl apply -k k8s/`.

---

## Quickstart & Verification

### 1. Start Minikube
```bash
minikube start --cpus=2 --memory=4096 --driver=docker
minikube addons enable ingress
```

### 2. Deploy the Stack
Deploy in dependency order:
```bash
# 1. Foundation & Storage
kubectl apply -f k8s/00-namespace.yaml
kubectl apply -f k8s/01-configmap.yaml
kubectl apply -f k8s/02-secret.yaml
kubectl apply -f k8s/03-storage.yaml

# 2. Database & Redis (Wait for readiness)
kubectl apply -f k8s/04-mariadb.yaml
kubectl apply -f k8s/05-redis.yaml
kubectl rollout status statefulset/mariadb -n frappe-crm --timeout=180s
kubectl wait --for=condition=available deployment/redis-cache deployment/redis-queue deployment/redis-socketio -n frappe-crm --timeout=90s

# 3. Initialize Site (Wait for completion)
kubectl apply -f k8s/06-frappe-init-job.yaml
kubectl wait --for=condition=complete job/frappe-site-init -n frappe-crm --timeout=300s

# 4. Workloads & Ingress
kubectl apply -f k8s/07-frappe-web.yaml
kubectl apply -f k8s/08-frappe-socketio.yaml
kubectl apply -f k8s/09-frappe-worker.yaml
kubectl apply -f k8s/10-frappe-scheduler.yaml
kubectl apply -f k8s/11-ingress.yaml
kubectl wait --for=condition=available deployment/frappe-web deployment/frappe-socketio deployment/frappe-worker deployment/frappe-scheduler -n frappe-crm --timeout=120s
```

### 3. Open in Browser

Run the port-forward command:
```bash
kubectl port-forward -n frappe-crm svc/frappe-web-svc 8080:80
```

Open: **[http://localhost:8080/login](http://localhost:8080/login)**

* **Username**: `Administrator`
* **Password**: `admin`

---

## Helpful Commands

```bash
# Check status of all resources
kubectl get all,pvc,ingress -n frappe-crm

# View web access & error logs
kubectl logs -n frappe-crm deployment/frappe-web -c nginx -f

# View Gunicorn application logs
kubectl logs -n frappe-crm deployment/frappe-web -c frappe-gunicorn -f

# Test API connectivity
curl -s http://localhost:8080/api/method/frappe.ping
```
