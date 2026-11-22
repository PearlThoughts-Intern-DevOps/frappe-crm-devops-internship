# Trivy Dependency Scan Evidence

## Scope
- Scanner: Trivy 0.76.2
- Scan type: Filesystem dependency vulnerability scan
- Scanned repository manifests and dependency files
- Seven dependency manifests were identified.
- Trivy detected three language-specific dependency files for analysis.
- No dependency lockfiles were found.

## Results

| Severity | Findings |
|---|---:|
| Critical | 0 |
| High | 43 |
| Medium | 33 |
| Low | 21 |
| Total | 97 |

## Coverage limitations

Although seven dependency manifests were identified, Trivy detected only three language-specific files for analysis. Therefore, these results do not represent complete coverage of every dependency declared in the repository.

The absence of lockfiles also limits the ability to verify exact resolved dependency versions. Findings should be reviewed and dependencies updated where fixes are available.

The scan excluded `.git`, `node_modules`, Docker recovery backups, and the DevSecOps output directory.
