# Frappe CRM — Docker Container Health & Recovery Report

**Report Generated:** 2026-11-05T12:03:22.400236+00:00  
**Target Project:** `crm`  
**System Status:** 🟢 **HEALTHY**  
**Report ID:** `report_20261105_120322`

---

## 1. Executive Summary

| Metric | Value | Threshold / Target |
| :--- | :--- | :--- |
| **Overall Health** | HEALTHY | `HEALTHY` |
| **Total Containers** | `4` | — |
| **Running Containers** | `4` / `4` | 100% |
| **Stopped Containers** | `0` | `0` |
| **Unhealthy Containers** | `0` | `0` |
| **High Resource Warnings** | `0` | `0` |
| **Total CPU Consumption** | `19.12%` | Threshold: `80.0%` |
| **Total Memory Usage** | `899.3 MiB` | Threshold: `80.0%` |
| **Log Errors Detected** | `0` | `0` |
| **Auto-Recovery Attempts** | `1` (Succeeded: `1`) | 100% Self-Healing |

---

## 2. Container Health & Telemetry

| Container Name | Service | Status | Health | CPU% | Memory (Usage / Limit) | PIDs | Uptime |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `crm-worker-test` | `worker` | 🟢 running | ✅ OK | `0.0%` | `2.7 MiB` / `7.4 GiB` (0.0%) | `4` | Just recovered |
| `crm-redis-1` | `redis` | 🟢 running | ✅ OK | `0.4%` | `12.9 MiB` / `7.4 GiB` (0.2%) | `6` | 2d 0h 24m |
| `crm-frappe-1` | `frappe` | 🟢 running | ✅ OK | `18.7%` | `595.6 MiB` / `7.4 GiB` (7.8%) | `35` | 2d 0h 24m |
| `crm-mariadb-1` | `mariadb` | 🟢 running | ✅ OK | `0.1%` | `290.8 MiB` / `7.4 GiB` (3.8%) | `8` | 2d 0h 24m |

---

## 3. Container Network & Application Health Probes

| Container | IP Address | Port Mappings | Probe Status | Probe Response / Latency |
| :--- | :--- | :--- | :--- | :--- |
| `crm-worker-test` | `172.18.0.5` | Internal only | ✅ `OK` | Background worker process running (0.0 ms) |
| `crm-redis-1` | `172.18.0.2` | 6379/tcp | ✅ `OK` | Redis daemon running on internal network port 6379 (0.0 ms) |
| `crm-frappe-1` | `172.18.0.3` | 0.0.0.0:8000->8000/tcp<br>0.0.0.0:9000->9000/tcp | ✅ `OK` | HTTP 200 /api/method/frappe.ping (94.31 ms) |
| `crm-mariadb-1` | `172.18.0.4` | 3306/tcp | ✅ `OK` | MariaDB daemon running on internal network port 3306 (0.0 ms) |

---

## 4. Container Log & Anomaly Analysis

| Container | Lines Analyzed | Errors | Warnings | Detected Error Categories |
| :--- | :--- | :--- | :--- | :--- |
| `crm-worker-test` | `15` | `0` | `0` | _None_ |
| `crm-redis-1` | `100` | `0` | `0` | _None_ |
| `crm-frappe-1` | `100` | `0` | `0` | _None_ |
| `crm-mariadb-1` | `100` | `0` | `23` | `WARNING`: 11, `DATABASE_ERROR`: 12 |

---

## 5. Automated Recovery & Self-Healing Actions

| Timestamp | Container | Initial Status | Action | Outcome | Duration | Notes |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `2026-11-05T12:03:18.112000+00:00` | `crm-worker-test` | `exited` | `restart` | 🟢 Succeeded | `4.12s` | Container 'crm-worker-test' successfully recovered and returned to 'running' state |

---

## 6. Active Alerts & Operational Recommendations

- ℹ️ **crm-worker-test: Self-healing recovery succeeded.**
- ✅ **All Frappe CRM containers are currently running, healthy, and operational.**

