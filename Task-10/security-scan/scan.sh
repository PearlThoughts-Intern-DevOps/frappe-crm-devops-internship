#!/bin/bash
# Run from the repo root:  bash Task-10/security-scan/scan.sh
R="$PWD/Task-10/security-scan/reports"
mkdir -p "$R/trivy-images"

# 1. Find the Docker images used by the project
grep -rhE --include='docker-compose*.yml' '^[[:space:]]*image:' . \
  | awk '{print $2}' | tr -d "\"'" | grep -v '\$' | sort -u > "$R/images-found.txt"
echo "Images to scan:"; cat "$R/images-found.txt"

# 2. Trivy: scan each image
while read -r img; do
  name=$(echo "$img" | tr '/:' '__')
  docker run --rm -v trivy-cache:/root/.cache -v "$R/trivy-images":/out \
    aquasec/trivy:latest image --scanners vuln --format json \
    --output "/out/$name.json" "$img" \
  && docker run --rm -v "$R/trivy-images":/out aquasec/trivy:latest convert \
    --format table --output "/out/$name.txt" "/out/$name.json" \
  || echo "SCAN FAILED for $img"
done < "$R/images-found.txt"

# 3. Trivy: scan dependencies (lock files)
docker run --rm -v trivy-cache:/root/.cache -v "$PWD":/project -v "$R":/out \
  aquasec/trivy:latest fs /project --scanners vuln --format json \
  --output /out/trivy-dependencies.json
docker run --rm -v "$R":/out aquasec/trivy:latest convert \
  --format table --output /out/trivy-dependencies.txt /out/trivy-dependencies.json

# 4. Gitleaks: scan git history for secrets
docker run --rm --user "$(id -u):$(id -g)" -v "$PWD":/repo -v "$R":/out \
  ghcr.io/gitleaks/gitleaks:latest git /repo --redact --exit-code 0 \
  --report-format json --report-path /out/gitleaks.json

# 5. Checkov: scan Dockerfiles and Kubernetes files
docker run --rm -v "$PWD":/src -v "$R":/out bridgecrew/checkov:latest \
  -d /src --framework dockerfile kubernetes --compact --soft-fail \
  -o cli -o json --output-file-path /out
mv "$R/results_cli.txt" "$R/checkov.txt"
mv "$R/results_json.json" "$R/checkov.json"

# 6. Summary
counts() {
  for sev in CRITICAL HIGH MEDIUM LOW; do
    n=$(jq "[.Results[]?.Vulnerabilities[]? | select(.Severity==\"$sev\")] | length" "$1")
    printf "%s=%s  " "$sev" "$n"
  done
}
top() {
  jq -r '[.Results[]?.Vulnerabilities[]?] | (map(select(.Severity=="CRITICAL")) + map(select(.Severity=="HIGH"))) | .[:10][] | "    - \(.Severity) \(.VulnerabilityID) \(.PkgName) \(.InstalledVersion) (fixed in: \(.FixedVersion // "no fix yet"))"' "$1"
}
{
  echo "# Scan summary"
  for f in "$R"/trivy-images/*.json; do
    [ -f "$f" ] || continue
    echo "- $(basename "$f" .json): $(counts "$f")"
    top "$f"
  done
  echo "- dependencies: $(counts "$R/trivy-dependencies.json")"
  echo "- dependency files checked: $(jq -r '[.Results[]?.Target] | join(", ")' "$R/trivy-dependencies.json")"
  top "$R/trivy-dependencies.json"
  echo "- gitleaks leaks: $(jq length "$R/gitleaks.json" 2>/dev/null || echo 'report missing')"
  echo "- checkov failed: $(jq 'if type=="array" then ([.[].summary.failed] | add) else .summary.failed end' "$R/checkov.json" 2>/dev/null || echo 'see checkov.txt')"
} | tee "$R/SUMMARY.md"