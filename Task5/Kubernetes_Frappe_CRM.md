# Task 5: Kubernetes Exploration, Architecture & Frappe CRM Deployment Guide

## Executive Summary

As modern enterprise software transitions from monolithic virtual machines to microservices, container orchestration has become the standard for deployment, scaling, and fault tolerance. This report details the architectural exploration and deployment strategy for containerizing **Frappe CRM** on **Kubernetes**, tested locally using **Minikube**.

Frappe CRM is a decoupled Single Page Application (Vue 3 + Vite) powered by a Python backend (Frappe Framework v15). Unlike simple stateless applications, Frappe CRM encompasses a multi-tier stateful architecture comprising:
1. **Relational Database**: MariaDB 10.6 LTS configured with `utf8mb4` character encoding.
2. **In-Memory Cache & Message Brokers**: Three isolated Redis instances for operational caching, async job queues, and WebSocket pub/sub.
3. **Application & Web Tier**: Gunicorn WSGI Python backend coupled with an NGINX reverse proxy for compiled static assets.
4. **Real-time Engine**: Dedicated Node.js process managing Socket.IO WebSockets.
5. **Asynchronous Background Workers**: Redis Queue (RQ) workers processing background tasks.
6. **Task Scheduler**: Singleton cron dispatcher executing periodic system jobs.

This document examines Kubernetes system architecture, analyzes core primitives and storage patterns, deconstructs Frappe's container requirements, and presents an end-to-end Minikube deployment and troubleshooting playbook.

---

## 1. Kubernetes Architectural Foundations

Kubernetes is a declarative, distributed container orchestration platform. It is split logically into two structural planes: the **Control Plane** (the cluster's brain) and **Worker Nodes** (where compute workloads run).

```text
┌────────────────────────────────────────────────────────────────────────────────────────┐
│                        KUBERNETES CONTROL PLANE (MASTER NODE)                          │
│                                                                                        │
│   ┌───────────────────────┐      Raft Sync      ┌──────────────────────────────────┐   │
│   │ kube-scheduler        │ ◄─────────────────► │ etcd                             │   │
│   │ (Resource Placement)  │                     │ (Distributed Key-Value Store)    │   │
│   └───────────┬───────────┘                     └────────────────┬─────────────────┘   │
│               │                                                  │                     │
│               ▼                                                  ▼                     │
│   ┌────────────────────────────────────────────────────────────────────────────────┐   │
│   │                        kube-apiserver (API Server)                             │   │
│   │          • Central REST Gateway        • Authentication & RBAC                 │   │
│   │          • Request Validation          • Admission Controllers                 │   │
│   └───────────────────────┬──────────────────────────────┬─────────────────────────┘   │
│                           ▲                              ▲                             │
│                           │                              │                             │
│               ┌───────────┴───────────┐      ┌───────────┴───────────┐                 │
│               │ kube-controller-mgr   │      │ cloud-controller-mgr  │                 │
│               │ (Node/Replica Loops)  │      │ (Cloud API Adapter)   │                 │
│               └───────────────────────┘      └───────────────────────┘                 │
└───────────────────────────┬──────────────────────────────┬─────────────────────────────┘
                            │                              │
                            │ Secure TLS                   │ Watch Events
                            ▼                              ▼
┌────────────────────────────────────────────────────────────────────────────────────────┐
│                        WORKER NODE (COMPUTE & WORKLOAD LAYER)                          │
│                                                                                        │
│   ┌──────────────────────────────────────┐    ┌────────────────────────────────────┐   │
│   │ kubelet (Node Agent)                 │    │ kube-proxy (Networking Engine)     │   │
│   │ • Syncs PodSpecs with API Server     │    │ • Maintains iptables / IPVS rules  │   │
│   │ • Manages Pod Lifecycle & Health     │    │ • Service ClusterIP load balancing │   │
│   └──────────────────┬───────────────────┘    └────────────────┬───────────────────┘   │
│                      │                                         │                       │
│                      ▼                                         │                       │
│   ┌──────────────────────────────────────┐                     │                       │
│   │ CRI Engine (containerd / CRI-O)      │                     │                       │
│   │ • Pulls images & sets cgroups/ns     │                     │                       │
│   └──────────────────┬───────────────────┘                     │                       │
│                      │                                         │                       │
│                      ▼                                         ▼                       │
│   ┌────────────────────────────────────────────────────────────────────────────────┐   │
│   │ Managed Pods:                                                                  │   │
│   │ [ Pod: mariadb ]       [ Pod: frappe-web ]       [ Pod: redis instances ]      │   │
│   └────────────────────────────────────────────────────────────────────────────────┘   │
└────────────────────────────────────────────────────────────────────────────────────────┘
```

### Control Plane Components

1. **`kube-apiserver` (API Server)**:
   - The central nervous system of Kubernetes.
   - Exposes the Kubernetes HTTP REST API consumed by `kubectl`, workers, and internal controllers.
   - Authenticates and authorizes requests (via RBAC, Webhooks) and validates object schemas before committing them.
   - The *only* component that communicates directly with `etcd`.

2. **`etcd` (Cluster State Store)**:
   - A highly available, consistent distributed key-value store based on the **Raft consensus algorithm**.
   - Serves as the single source of truth for the entire cluster (storing specifications, runtime statuses, secrets, and configurations).
   - Watch APIs allow controllers to react instantaneously to state mutations.

3. **`kube-scheduler` (Resource Matcher & Scheduler)**:
   - Monitors newly created Pods that have no assigned node.
   - Evaluates node resource capacity (CPU, RAM), node affinity/anti-affinity, taints and tolerations, and data locality to select the optimal Worker Node for each pod.

4. **`kube-controller-manager` (State Reconciler)**:
   - Runs continuous control loops (reconciliation cycles) that compare the **current state** against the **desired state**.
   - Subsumes internal controllers: Node Controller, ReplicaSet Controller, EndpointSlice Controller, and ServiceAccount Controller.

5. **`cloud-controller-manager`**:
   - Integrates platform-specific cloud APIs (e.g., AWS NLB, GCP Cloud Load Balancing, Azure Managed Disks) without tying core Kubernetes code to cloud providers.

### Worker Node Components

1. **`kubelet`**:
   - An agent running on each worker node.
   - Communicates with the API Server to receive `PodSpecs`.
   - Interfaces with the local Container Runtime via the Container Runtime Interface (CRI) to pull container images, run containers, mount volumes, and report container liveness/readiness statuses back to the control plane.

2. **`kube-proxy`**:
   - Network proxy running on every worker node.
   - Maintains network rules on host interfaces (via `iptables` or `IPVS`) to implement Kubernetes `Service` abstractions.
   - Translates virtual `ClusterIP` traffic into direct container network endpoints with round-robin load distribution.

3. **Container Runtime Engine (CRI)**:
   - Low-level software executing containers (e.g., `containerd`, `CRI-O`).
   - Implements OCI specifications to construct isolated Linux namespaces (PID, NET, MNT, UTS, IPC) and cgroups (CPU, memory, I/O limits).

---

## 2. Core Kubernetes Primitives & Object Model

Kubernetes manages infrastructure declaratively via YAML manifests. The core objects utilized in the Frappe CRM deployment are:

| Resource Kind | Purpose in Kubernetes | Role in Frappe CRM Setup |
|---|---|---|
| **Namespace** | Logical partitioning of cluster resources | `frappe-crm` isolates CRM workloads from system pods |
| **Pod** | Smallest schedulable unit; 1+ tightly coupled containers sharing network & storage | Multi-container web pod (`nginx` + `gunicorn`) |
| **Deployment** | Declarative management of stateless replica sets with rolling updates | Manages `redis`, `frappe-web`, `frappe-worker`, `frappe-scheduler` |
| **StatefulSet** | Ordered deployment and sticky network identity for stateful workloads | Manages `mariadb` with dedicated persistent storage |
| **Service** | Stable L4 networking abstraction and internal DNS endpoint | `mariadb-svc`, `redis-cache-svc`, `frappe-web-svc` |
| **Job** | Run-to-completion batch execution | `frappe-site-init` runs one-time site setup and migrations |
| **ConfigMap** | Decouples non-sensitive configuration artifacts from container images | Injects DB hosts, Redis URLs, `frappe.cnf`, and `nginx.conf` |
| **Secret** | Obfuscated storage for sensitive keys and credentials | Securely stores MariaDB root password and administrator secret |
| **PersistentVolumeClaim** | Request for durable storage bound to host or cloud disks | Retains database tables (`mariadb-data-pvc`) and files (`frappe-sites-pvc`) |
| **Ingress** | L7 HTTP/HTTPS reverse proxy and domain routing | Directs `crm.localhost` traffic to `frappe-web-svc:80` |

---

## 3. Storage Architecture: PV, PVC, and Storage Classes

Containers have ephemeral filesystems; when a container crashes or is rescheduled, any uncommitted disk writes are destroyed. Frappe CRM requires persistent durability for database tables, uploaded user files (PDFs, avatars, lead attachments), and compiled static assets.

```text
┌────────────────────────────────────────────────────────────────────────────────────────┐
│                              KUBERNETES STORAGE ABSTRACTION                            │
│                                                                                        │
│   ┌────────────────────────────────┐        Requests Dynamic Binding                   │
│   │ PersistentVolumeClaim (PVC)    │ ──────────────────────────────────────┐          │
│   │ Developer Storage Request      │                                       │          │
│   │ (e.g. 10Gi, ReadWriteMany)     │                                       ▼          │
│   └────────────────────────────────┘                       ┌───────────────────────┐  │
│                                                            │ StorageClass          │  │
│                                                            │ Provisioning Template │  │
│                                                            │ (standard / hostpath) │  │
│                                                            └───────────┬───────────┘  │
│                                                                        │              │
│                                     Dynamically Provisions             │              │
│   ┌────────────────────────────────┐ ◄─────────────────────────────────┘              │
│   │ PersistentVolume (PV)          │                                                  │
│   │ Cluster Storage Unit (Bound)   │                                                  │
│   └───────────────┬────────────────┘                                                  │
│                   │                                                                   │
│                   ▼ Backs                                                             │
│   ┌────────────────────────────────┐                                                  │
│   │ Physical Storage Medium        │                                                  │
│   │ (Local HostPath / Cloud Volume)│                                                  │
│   └────────────────────────────────┘                                                  │
└────────────────────────────────────────────────────────────────────────────────────────┘
```

### PV vs. PVC Abstraction
- **PersistentVolume (PV)**: A piece of physical storage provisioned in the cluster (e.g., a local disk partition, AWS EBS volume, or NFS export). It exists independently of any pod lifecycle.
- **PersistentVolumeClaim (PVC)**: A request for storage by a user/workload. It specifies the desired capacity (e.g., `10Gi`) and access mode (`ReadWriteOnce`, `ReadWriteMany`).
- **StorageClass**: Enables **Dynamic Provisioning**. When a PVC is created without a statically assigned PV, the StorageClass invokes an underlying volume plugin (e.g., Kubernetes `hostpath-provisioner` on Minikube, or `ebs.csi.aws.com` on AWS) to create the volume on-demand.

### Access Modes & Frappe CRM Requirements

1. **`ReadWriteOnce` (RWO)**:
   - Volume can be mounted as read-write by a **single node** at any given time.
   - **Applied to**: `mariadb-data-pvc` (MariaDB storage). Database engines require single-instance locking over physical data directories (`/var/lib/mysql`) to prevent index and table corruption.

2. **`ReadWriteMany` (RWX)**:
   - Volume can be mounted as read-write concurrently by **multiple nodes**.
   - **Applied to**: `frappe-sites-pvc`. Multiple pods (`frappe-web`, `frappe-worker`, `frappe-scheduler`, `frappe-site-init`) must simultaneously read and write to the shared `/home/frappe/frappe-bench/sites` directory (for `site_config.json`, encryption keys, and uploaded assets).
   - **Minikube vs. Cloud Environments**:
     > [!NOTE]
     > On **Minikube**, the default `standard` hostPath provisioner satisfies `ReadWriteMany` because all pods run on the same virtual machine node, mounting the same underlying host path.
     > In **multi-node production cloud clusters** (EKS, GKE, AKS), block storage (AWS EBS, GCP Persistent Disk) **only supports RWO**. A distributed network filesystem (AWS EFS, GCP Filestore, Azure Files, or CephFS) must be provisioned via a custom StorageClass to satisfy RWX.

---

## 4. Deconstructing Frappe CRM for Cloud-Native Orchestration

Frappe was originally architected to run inside a single virtual machine governed by the `bench` CLI managing local systemd or Supervisord processes. Porting Frappe CRM to Kubernetes requires decomposing these tightly coupled components into independent, scalable microservices.

```text
┌────────────────────────────────────────────────────────────────────────────────────────┐
│                                  CLIENT INGRESS LAYER                                  │
│                                                                                        │
│   Browser Request ──► [ Ingress: crm.localhost:80 ] ──► [ Service: frappe-web-svc ]   │
└────────────────────────────────────────┬───────────────────────────────────────────────┘
                                         │
                                         ▼
┌────────────────────────────────────────────────────────────────────────────────────────┐
│ APPLICATION & REAL-TIME WORKLOADS                                                      │
│                                                                                        │
│   ┌──────────────────────── frappe-web Pod (Dual-Container) ────────────────────────┐  │
│   │                                                                                 │  │
│   │   [ Container 1: NGINX (8080) ] ────────► Serves /assets & /files from volume   │  │
│   │          │                     ────────► Reverse proxies / to Gunicorn          │  │
│   │          │                     ────────► Upgrades & proxies /socket.io          │  │
│   │          ▼                                                 │                    │  │
│   │   [ Container 2: Gunicorn (8000) ] (WSGI Python API)       │                    │  │
│   └──────────────────┬─────────────────────────────────────────┼────────────────────┘  │
│                      │                                         │                       │
│                      │                                         ▼                       │
│                      │                              ┌───────────────────────┐          │
│                      │                              │ frappe-socketio Pod   │          │
│                      │                              │ (Node.js Port 9000)   │          │
│                      │                              └──────────┬────────────┘          │
│                      ▼                                         │                       │
│   ┌─────────────────────────────────────┐                      │                       │
│   │ Background Workers & Scheduler      │                      │                       │
│   │ • frappe-worker Pod (RQ Worker)     │                      │                       │
│   │ • frappe-scheduler Pod (Cron)       │                      │                       │
│   └──────────────────┬──────────────────┘                      │                       │
└──────────────────────┼─────────────────────────────────────────┼───────────────────────┘
                       │                                         │
                       ▼                                         ▼
┌────────────────────────────────────────────────────────────────────────────────────────┐
│ DATA & BROKER INFRASTRUCTURE                                                           │
│                                                                                        │
│   ┌────────────────────────┐    ┌─────────────────────┐    ┌───────────────────────┐   │
│   │ MariaDB 10.6 StatefulSet│    │ Redis Cache         │    │ Redis Queue           │   │
│   │ (mariadb-svc:3306)     │    │ (redis-cache-svc)   │    │ (redis-queue-svc)     │   │
│   └──────────┬─────────────┘    └─────────────────────┘    └───────────────────────┘   │
│              │                                                         ▲               │
│              │                  ┌────────────────────────┐             │               │
│              │                  │ Redis Socket.IO        │ ◄───────────┘               │
│              │                  │ (redis-socketio-svc)   │                             │
│              │                  └────────────────────────┘                             │
└──────────────┼─────────────────────────────────────────────────────────────────────────┘
               │
               ▼
┌────────────────────────────────────────────────────────────────────────────────────────┐
│ PERSISTENT STORAGE CLAIMS                                                              │
│                                                                                        │
│   [ mariadb-data-pvc ] (5Gi - RWO) ───────► Backs MariaDB /var/lib/mysql               │
│   [ frappe-sites-pvc ] (10Gi - RWX) ──────► Shared /home/frappe/frappe-bench/sites    │
└────────────────────────────────────────────────────────────────────────────────────────┘
```

### Architectural Analysis & Critical Design Decisions

#### 1. Container Image Strategy: Option A vs. Option B
- **Option A (Anti-pattern)**: Using `frappe/bench:latest` and running `bench init` and `bench get-app crm` at runtime inside a Kubernetes Job.
  - *Why it fails*: It downloads gigabytes of dependencies (`pip`, `yarn`) over the network on every deployment, risking network timeouts and OOMKills. Furthermore, files written to `/home/frappe/frappe-bench/apps` reside on the container's ephemeral root filesystem; when the Job terminates, the compiled Python modules vanish, causing `ModuleNotFoundError: No module named 'crm'` in subsequent pods.
- **Option B (Production Standard)**: Using a **pre-baked, layered container image** (`ghcr.io/frappe/crm:stable`). The image contains all Python virtual environments, compiled wheels, and Frappe UI Vue bundles baked in at build time. Runtime jobs are restricted strictly to configuring database credentials and running schema migrations.

#### 2. Dual-Container Web Pod & The NGINX Reverse Proxy
- **Static Assets Dilemma**: Gunicorn is a pure Python WSGI application server. In production mode, Gunicorn does **not** serve static files (compiled JavaScript/CSS in `/assets/crm/...` or user attachments in `/files/...`). Direct requests to Gunicorn for static assets result in HTTP `404 Not Found`, rendering a blank screen in the user's browser.
- **The Solution**: Coupling `nginx:alpine` alongside Gunicorn inside the same `frappe-web` Pod. NGINX directly serves static assets from `/home/frappe/frappe-bench/sites/assets` using zero-copy Linux `sendfile`, while proxying dynamic `/api` calls to Gunicorn at `127.0.0.1:8000` and WebSocket requests to `frappe-socketio-svc:9000`.

#### 3. Dedicated Socket.IO Node.js Microservice
- Real-time desk notifications, presence, and chat events in Frappe are powered by Node.js (`apps/frappe/socketio.js`). Gunicorn cannot serve these WebSocket protocols. A dedicated `frappe-socketio` Deployment connects to `redis-socketio` to broadcast live push updates across cluster nodes.

#### 4. MariaDB 10.6 LTS with Safe ConfigMap SubPath Mounting
- Frappe Framework v15 officially targets **MariaDB 10.6 LTS**. MariaDB 10.8 reached End-of-Life in May 2023.
- To enforce Frappe's strict database requirements (`utf8mb4`, `skip-character-set-client-handshake`), we mount `my.cnf` into `/etc/mysql/conf.d/frappe.cnf`. Using Kubernetes `subPath: frappe.cnf` ensures the container's native `/etc/mysql` configuration directory is preserved without being overwritten by the volume mount.

#### 5. Scheduler Singleton Pattern (`strategy: Recreate`)
- Frappe's `bench schedule` checks the database and pushes recurring tasks into `redis-queue`.
- If a standard `RollingUpdate` strategy is used during upgrades, two scheduler pods briefly run in parallel. This causes race conditions where scheduled events (such as hourly email syncs or lead scoring) are queued twice. Configuring `strategy: { type: Recreate }` and `replicas: 1` guarantees strict singleton semantics.

---

## 5. Kubernetes Manifest Reference (`k8s/`)

The repository contains declarative specifications inside the [`k8s/`](file:///home/devangkore17/Desktop/Internship_Project/frappe-crm-devops-internship/k8s/) directory:

```
k8s/
├── 00-namespace.yaml          # Isolates workloads in 'frappe-crm'
├── 01-configmap.yaml          # Frappe site, MariaDB, and NGINX configurations
├── 02-secret.yaml             # DB root, admin passwords, encryption secrets
├── 03-storage.yaml            # mariadb-data-pvc (5Gi) and frappe-sites-pvc (10Gi)
├── 04-mariadb.yaml            # MariaDB 10.6 StatefulSet + ClusterIP Service
├── 05-redis.yaml              # Dedicated redis-cache, redis-queue, redis-socketio
├── 06-frappe-init-job.yaml    # Idempotent bench initialization Job
├── 07-frappe-web.yaml         # Dual-container Pod (NGINX + Gunicorn) + NodePort
├── 08-frappe-socketio.yaml    # Node.js WebSocket service for real-time events
├── 09-frappe-worker.yaml      # Scalable RQ queue background workers
├── 10-frappe-scheduler.yaml   # Singleton task scheduler (strategy: Recreate)
├── 11-ingress.yaml            # Ingress routing crm.localhost to frappe-web-svc
└── kustomization.yaml         # Declarative resource index for Kustomize
```

---

## 6. Minikube Deployment Playbook

Follow these exact steps to bootstrap, configure, deploy, and verify Frappe CRM in a local Minikube environment.

### Step 1: Cluster Initialization
Allocate at least 2 vCPUs and 4096 MB RAM to accommodate MariaDB, the Redis trio, and the Python application workers:

```bash
# Start Minikube with required compute allocations
minikube start --cpus=2 --memory=4096 --driver=docker

# Enable the NGINX Ingress controller addon
minikube addons enable ingress

# Verify ingress controller readiness
kubectl wait --namespace ingress-nginx \
  --for=condition=ready pod \
  --selector=app.kubernetes.io/component=controller \
  --timeout=120s
```

### Step 2: Staged, Dependency-Gated Deployment

Deploying complex distributed applications requires phased rollouts to prevent pods from crashing before their storage and backing databases are accessible.

```bash
# Phase 1: Namespace, Configuration, Secrets, and Persistent Storage Claims
kubectl apply -f k8s/00-namespace.yaml
kubectl apply -f k8s/01-configmap.yaml
kubectl apply -f k8s/02-secret.yaml
kubectl apply -f k8s/03-storage.yaml

# Phase 2: Stateful Data & Cache Layer (Wait for Healthy Readiness)
kubectl apply -f k8s/04-mariadb.yaml
kubectl apply -f k8s/05-redis.yaml
kubectl rollout status statefulset/mariadb -n frappe-crm --timeout=180s
kubectl wait --for=condition=available deployment/redis-cache deployment/redis-queue deployment/redis-socketio -n frappe-crm --timeout=90s

# Phase 3: Site Initialization & Database Schema Provisioning
kubectl apply -f k8s/06-frappe-init-job.yaml
kubectl wait --for=condition=complete job/frappe-site-init -n frappe-crm --timeout=300s

# Phase 4: Application Workloads, Background Workers, Scheduler & Ingress
kubectl apply -f k8s/07-frappe-web.yaml
kubectl apply -f k8s/08-frappe-socketio.yaml
kubectl apply -f k8s/09-frappe-worker.yaml
kubectl apply -f k8s/10-frappe-scheduler.yaml
kubectl apply -f k8s/11-ingress.yaml
kubectl wait --for=condition=available deployment/frappe-web deployment/frappe-socketio deployment/frappe-worker deployment/frappe-scheduler -n frappe-crm --timeout=120s
```

### Step 3: Domain Resolution & Ingress Access
Map `crm.localhost` to the Minikube virtual IP:

```bash
# Extract Minikube IP address
MINIKUBE_IP=$(minikube ip)

# Append domain mapping to local /etc/hosts
echo "${MINIKUBE_IP} crm.localhost" | sudo tee -a /etc/hosts
```

You can now open your browser and navigate to:
- **Primary Ingress URL**: [http://crm.localhost](http://crm.localhost)
- **NodePort Fallback URL**: `minikube service frappe-web-svc -n frappe-crm --url`
- **Default Credentials**: Username: `Administrator`, Password: `admin`

---

## 7. Cluster Observability & Health Verification

Once deployed, execute the following commands to confirm operational health across all layers:

### 1. Workload & Service Inspection
```bash
# Check status of all pods, services, and statefulsets in the namespace
kubectl get all -n frappe-crm

# Verify PVC binding status (must show STATUS: Bound)
kubectl get pvc -n frappe-crm
```

### 2. Testing HTTP & API Connectivity
```bash
# Verify Frappe Ping API through the NodePort service
curl -I http://$(minikube ip):30080/api/method/frappe.ping

# Verify Ingress routing with explicit Host headers
curl -I -H "Host: crm.localhost" http://$(minikube ip)/crm
```

### 3. Validating Inter-Service DNS Resolution
Verify that application pods can resolve and reach MariaDB and Redis services internally:
```bash
# Run a one-off diagnostic container inside the cluster
kubectl run dns-test -it --rm --namespace=frappe-crm --image=busybox:1.36 --restart=Never -- sh

# Inside the test container, run:
nslookup mariadb-svc.frappe-crm.svc.cluster.local
nc -zv mariadb-svc 3306
nc -zv redis-cache-svc 6379
```

---

## 8. Practical Troubleshooting & Failure Diagnostics

When managing containerized workloads in Kubernetes, issues generally manifest as pod lifecycle failures. The standard debugging workflow proceeds as follows:

```text
┌────────────────────────────────────────────────────────────────────────────────────────┐
│                        KUBERNETES DIAGNOSTIC DECISION WORKFLOW                         │
│                                                                                        │
│                Step 1: Check Pod Status (kubectl get pods -n frappe-crm)               │
│                                           │                                            │
│            ┌──────────────────────────────┼─────────────────────────────┐              │
│            ▼                              ▼                             ▼              │
│   [ CrashLoopBackOff ]              [ Pending ]               [ ImagePullBackOff ]     │
│            │                              │                             │              │
│            ▼                              ▼                             ▼              │
│   Step 2: Inspect Logs           Step 3: Inspect Events        Step 4: Verify Image    │
│   kubectl logs <pod>             kubectl describe pod <pod>    Check image tag,        │
│   --previous -c <container>      kubectl describe pvc <pvc>    registry credentials    │
│            │                              │                             │              │
│            ▼                              ▼                             ▼              │
│   Action: Correct DB auth,       Action: Free CPU/RAM,         Action: Correct image   │
│   Redis URLs, or subPath mounts  verify PVC binding on node    name or add pull secrets│
└────────────────────────────────────────────────────────────────────────────────────────┘
```

### Scenario 1: `CrashLoopBackOff`
* **Symptoms**: The pod repeatedly starts, fails, terminates, and restarts with an exponential backoff.
* **Root Causes**:
  - MariaDB authentication failure (`Access denied for user 'root'`).
  - Gunicorn failing to bind because `site_config.json` is missing or corrupted on `frappe-sites-pvc`.
  - Redis connection refused due to misconfigured service DNS names.
* **Diagnostics**:
  ```bash
  # Check logs of the crashing container
  kubectl logs -n frappe-crm <pod-name> -c <container-name> --previous
  ```
* **Resolution**:
  - Verify secrets match in `02-secret.yaml`.
  - Check `site_config.json` on the mounted PVC using a debug shell.

### Scenario 2: `ImagePullBackOff` / `ErrImagePull`
* **Symptoms**: Pod status displays `ErrImagePull` or `ImagePullBackOff`.
* **Root Causes**: Typo in the container image repository/tag, rate-limiting on Docker Hub/GHCR, or missing `imagePullSecrets` for private registries.
* **Diagnostics**:
  ```bash
  kubectl describe pod -n frappe-crm <pod-name>
  ```
  Look for event messages: `Failed to pull image "...": rpc error: code = NotFound`.
* **Resolution**: Ensure the image name is valid (`ghcr.io/frappe/crm:stable`) and reachable from the Minikube VM.

### Scenario 3: `Pending` Pods & Storage Binding Deadlocks
* **Symptoms**: The pod remains perpetually in `Pending` state.
* **Root Causes**:
  - Insufficient CPU or memory requested versus available node capacity.
  - PVC cannot bind because no StorageClass matches or disk space is exhausted.
* **Diagnostics**:
  ```bash
  kubectl describe pod -n frappe-crm <pod-name>
  kubectl describe pvc -n frappe-crm <pvc-name>
  ```
* **Resolution**:
  - Check node resource pressure: `kubectl describe nodes`.
  - On Minikube, verify that `storage-provisioner` addon is running: `minikube addons list`.

### Scenario 4: Static Assets Returning HTTP 404 (Blank White Screen)
* **Symptoms**: Application loads, but CSS, JS bundles, and icons fail to load, resulting in an unstyled white screen.
* **Root Causes**: The NGINX reverse proxy cannot locate `/home/frappe/frappe-bench/sites/assets/` on `frappe-sites-pvc` because the initialization job did not populate assets, or volume paths do not match.
* **Diagnostics**:
  ```bash
  # View NGINX access and error logs
  kubectl logs -n frappe-crm deployment/frappe-web -c nginx -f
  ```
* **Resolution**: The `sync-assets` initContainer inside `07-frappe-web.yaml` automatically syncs bundled assets onto `frappe-sites-pvc` prior to NGINX startup, preventing this failure mode.

---

## Conclusion & Next Steps

Deploying Frappe CRM on Kubernetes transitions the application from a brittle, single-server setup to a resilient, self-healing, horizontally scalable cloud-native system. By decoupling the database into a `StatefulSet`, breaking Redis into specialized caching/queue instances, pairing Gunicorn with NGINX in a dual-container web pod, and externalizing storage via PVCs, the architecture achieves true high availability.

For future enhancements:
1. **Automated CI/CD**: Implement GitHub Actions workflows to build custom layered container images on code push and apply changes via Helm or ArgoCD.
2. **Cloud Migration**: Transition the Minikube manifests to managed cloud services (Amazon EKS with AWS EFS for RWX storage and RDS MariaDB for managed database persistence).
3. **Observability Stack**: Deploy Prometheus and Grafana with the MariaDB and Redis exporters to monitor cluster latency and queue depths.
