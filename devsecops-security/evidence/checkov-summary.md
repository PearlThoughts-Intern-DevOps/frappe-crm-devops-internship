# Checkov Kubernetes Scan Evidence

## Scope
- Scanner: Checkov 3.4.6
- Framework: Kubernetes
- Target: `devsecops-security/configs/kubernetes/`
- Manifests scanned: 9 YAML files

## Command

```powershell
docker run --rm -v "${manifestPath}:/k8s" bridgecrew/checkov -d /k8s --framework kubernetes --compact

## Results

| Result | Count |
|---|---:|
| Passed checks | 738 |
| Failed checks | 154 |
| Skipped checks | 0 |

The scan output is saved in `../scan-results/checkov-kubernetes.txt`.

## Interpretation

The 154 failed checks are policy findings requiring review and remediation prioritization. They should not be interpreted as 154 confirmed exploitable vulnerabilities. Some checks may require cluster-level context or manual assessment.

The scan was repeated against the nine Kubernetes manifests included in this submission. The results matched the earlier scan.
```
