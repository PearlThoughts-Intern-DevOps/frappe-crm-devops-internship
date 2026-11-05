# Frappe CRM — Docker Container Health & Monitoring Report

**Report Generated:** 2026-11-05T11:56:28.672773+00:00  
**Target Project:** `crm`  
**System Status:** 🟢 **HEALTHY**  
**Report ID:** `report_20261105_115628`

---

## 1. Executive Summary

| Metric | Value | Threshold / Target |
| :--- | :--- | :--- |
| **Overall Health** | HEALTHY | `HEALTHY` |
| **Total Containers** | `3` | — |
| **Running Containers** | `3` / `3` | 100% |
| **Stopped Containers** | `0` | `0` |
| **Unhealthy Containers** | `0` | `0` |
| **High Resource Warnings** | `0` | `0` |
| **Total CPU Consumption** | `17.97%` | Threshold: `80.0%` |
| **Total Memory Usage** | `898.6 MiB` | Threshold: `80.0%` |
| **Log Errors Detected** | `0` | `0` |
| **Auto-Recovery Attempts** | `0` (Succeeded: `0`) | — |

---

## 2. Container Health & Telemetry

| Container Name | Service | Status | Health | CPU% | Memory (Usage / Limit) | PIDs | Uptime |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `crm-redis-1` | `redis` | 🟢 running | ✅ OK | `0.3%` | `13.6 MiB` / `7.4 GiB` (0.2%) | `6` | 2d 0h 17m |
| `crm-frappe-1` | `frappe` | 🟢 running | ✅ OK | `17.6%` | `594.2 MiB` / `7.4 GiB` (7.8%) | `35` | 2d 0h 17m |
| `crm-mariadb-1` | `mariadb` | 🟢 running | ✅ OK | `0.1%` | `290.8 MiB` / `7.4 GiB` (3.8%) | `8` | 2d 0h 17m |

---

## 3. Container Network & Application Health Probes

| Container | IP Address | Port Mappings | Probe Status | Probe Response / Latency |
| :--- | :--- | :--- | :--- | :--- |
| `crm-redis-1` | `172.18.0.2` | 6379/tcp | ✅ `OK` | Redis daemon running on internal network port 6379 (0.0 ms) |
| `crm-frappe-1` | `172.18.0.3` | 0.0.0.0:8000->8000/tcp<br>:::8000->8000/tcp<br>0.0.0.0:9000->9000/tcp<br>:::9000->9000/tcp | ✅ `OK` | HTTP 200 /api/method/frappe.ping (90.94 ms) |
| `crm-mariadb-1` | `172.18.0.4` | 3306/tcp | ✅ `OK` | MariaDB daemon running on internal network port 3306 (0.0 ms) |

---

## 4. Container Log & Anomaly Analysis

| Container | Lines Analyzed | Errors | Warnings | Detected Error Categories |
| :--- | :--- | :--- | :--- | :--- |
| `crm-redis-1` | `100` | `0` | `0` | _None_ |
| `crm-frappe-1` | `100` | `0` | `0` | _None_ |
| `crm-mariadb-1` | `100` | `0` | `23` | `WARNING`: 11, `DATABASE_ERROR`: 12 |

### Error Snippets

**Container `crm-mariadb-1`:**
```text
2026-11-03T08:39:17.742483058Z 2026-11-03  8:39:17 0 [Warning] mariadbd: io_uring_queue_init() failed with errno 1
2026-11-03T08:39:17.742809262Z 2026-11-03  8:39:17 0 [Warning] InnoDB: liburing disabled: falling back to innodb_use_native_aio=OFF
2026-11-03T08:39:17.862948751Z 2026-11-03  8:39:17 0 [Warning] 'user' entry 'root@a7d101e2412e' ignored in --skip-name-resolve mode.
2026-11-03T08:39:17.862984594Z 2026-11-03  8:39:17 0 [Warning] 'proxies_priv' entry '@% root@a7d101e2412e' ignored in --skip-name-resolve mode.
2026-11-03T08:39:24.666664000Z 2026-11-03  8:39:24 0 [Warning] mariadbd: io_uring_queue_init() failed with errno 1
```

---

## 5. Automated Recovery & Self-Healing Actions

No recovery actions were required during this monitoring cycle.

---

## 6. Active Alerts & Operational Recommendations

- ✅ **All Frappe CRM containers are fully operational and within performance thresholds.**
