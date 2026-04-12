#!/bin/bash
# Scheduled API discovery — runs inside the app container once per month.
# Pulls candidates from the curated KNOWN_APIS list plus APIs.guru (capped
# at 200 entries by the Python script). Filters out tools already in the
# DB, so the first run assesses the bulk of new APIs and subsequent runs
# only touch whatever has been newly listed on APIs.guru.
#
# Install on the server with:
#   (crontab -l; echo "0 4 1 * * /home/nemoflow/nemoflow/scripts/run-discovery.sh") | crontab -

set -u
LOG="/home/nemoflow/nemoflow/discovery.log"
COMPOSE_DIR="/home/nemoflow/nemoflow"

# Keep the log from growing unbounded — rotate at 2MB
if [ -f "$LOG" ] && [ "$(stat -c %s "$LOG" 2>/dev/null || echo 0)" -gt 2000000 ]; then
    mv "$LOG" "${LOG}.1"
fi

{
    echo "=== $(date -Iseconds) discovery run starting ==="
    cd "$COMPOSE_DIR" || exit 1
    docker compose exec -T app python scripts/discover-apis.py --include-guru 2>&1
    echo "=== $(date -Iseconds) discovery run finished (exit=$?) ==="
    echo
} >> "$LOG"
