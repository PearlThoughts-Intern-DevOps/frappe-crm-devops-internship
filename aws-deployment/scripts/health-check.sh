#!/usr/bin/env bash

set -euo pipefail

URL="${1:-http://localhost:8080/api/method/ping}"
MAX_ATTEMPTS="${MAX_ATTEMPTS:-12}"
SLEEP_SECONDS="${SLEEP_SECONDS:-5}"

echo "Checking application health: ${URL}"

for attempt in $(seq 1 "$MAX_ATTEMPTS"); do
    if curl --fail --silent --show-error "$URL" >/dev/null; then
        echo "Application health check passed."
        exit 0
    fi

    echo "Attempt ${attempt}/${MAX_ATTEMPTS} failed."
    sleep "$SLEEP_SECONDS"
done

echo "Application health check failed."
exit 1
