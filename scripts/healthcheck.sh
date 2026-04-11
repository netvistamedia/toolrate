#!/bin/bash
# Simple health check — run via cron on the server
# Checks API health and restarts containers if down
# Add to crontab: */5 * * * * /home/nemoflow/nemoflow/scripts/healthcheck.sh

LOG="/home/nemoflow/nemoflow/healthcheck.log"
COMPOSE="/home/nemoflow/nemoflow"

response=$(curl -s -o /dev/null -w "%{http_code}" --max-time 10 http://localhost:8000/health 2>/dev/null)

if [ "$response" != "200" ]; then
    echo "$(date -Iseconds) ALERT: Health check failed (HTTP $response). Restarting..." >> "$LOG"
    cd "$COMPOSE" && docker compose restart app >> "$LOG" 2>&1
    sleep 10

    # Check again after restart
    response2=$(curl -s -o /dev/null -w "%{http_code}" --max-time 10 http://localhost:8000/health 2>/dev/null)
    if [ "$response2" != "200" ]; then
        echo "$(date -Iseconds) CRITICAL: Still down after restart (HTTP $response2)" >> "$LOG"
    else
        echo "$(date -Iseconds) RECOVERED: Back up after restart" >> "$LOG"
    fi
else
    # Only log once per hour to keep log small
    minute=$(date +%M)
    if [ "$minute" = "00" ]; then
        echo "$(date -Iseconds) OK" >> "$LOG"
    fi
fi
