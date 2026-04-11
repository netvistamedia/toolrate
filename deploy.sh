#!/bin/bash
set -e

SERVER="nemoflow@178.104.171.216"
REMOTE_DIR="~/nemoflow"

echo "Deploying NemoFlow..."

# Push latest code
git push origin main

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
