#!/bin/bash
set -e

SERVER="nemoflow@178.104.171.216"
REMOTE_DIR="~/nemoflow"

echo "Deploying NemoFlow..."

# Push latest code
git push origin main

# Wait for CI to start and finish
echo "Waiting for CI to pass..."
sleep 5
RUN_ID=$(gh run list --branch main --limit 1 --json databaseId --jq '.[0].databaseId')
if [ -n "$RUN_ID" ]; then
    gh run watch "$RUN_ID" --exit-status && echo "CI passed!" || { echo "CI failed — aborting deploy."; exit 1; }
fi

# Deploy on server
ssh $SERVER bash -s << 'REMOTE'
cd ~/nemoflow
git pull
docker compose up -d --build
docker compose exec -T app alembic upgrade head
docker compose exec -T app python scripts/manage-partitions.py || echo "Partition management skipped (may not be partitioned yet)"
echo "Deployed successfully!"
docker compose ps
REMOTE

echo "Done! https://api.nemoflow.ai"
