# Trivy Docker Image Scan Evidence

## Scope
- Scanner: Trivy 0.76.2
- Images scanned:
  - `mariadb:10.8`
  - `redis:alpine`
  - `frappe/bench:latest`

## Results

| Docker image | Critical | High | Medium | Low | Unknown | Total |
|---|---:|---:|---:|---:|---:|---:|
| mariadb:10.8 | 5 | 83 | 410 | 163 | 1 | 662 |
| redis:alpine | 0 | 0 | 1 | 0 | 0 | 1 |
| frappe/bench:latest | 13 | 935 | 1479 | 1369 | 46 | 3842 |

## Interpretation

The counts are scanner-reported findings, not necessarily unique CVEs or independently confirmed exploitable vulnerabilities. Findings require review against package versions, fix availability, and actual runtime exposure.

The `latest` image tag is mutable. For reproducible deployments, pin images to verified versions or digests and rescan regularly.

Raw Trivy JSON output was retained locally for analysis. It is not included in this evidence folder because automated secret scanning flagged strings in the generated reports that require separate false-positive review.
