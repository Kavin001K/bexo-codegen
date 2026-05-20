#!/usr/bin/env bash
# Run on the VM: cd ~/bexo-n8n && bash fix-n8n-env-access.sh
set -euo pipefail

COMPOSE_FILE="${COMPOSE_FILE:-docker-compose.micro.yml}"

cd "$(dirname "$0")" 2>/dev/null || cd ~/bexo-n8n

if [[ ! -f "$COMPOSE_FILE" ]]; then
  echo "Missing $COMPOSE_FILE"
  exit 1
fi

# .env: unblock + no accidental true
if grep -q '^N8N_BLOCK_ENV_ACCESS_IN_NODE=' .env 2>/dev/null; then
  sed -i 's/^N8N_BLOCK_ENV_ACCESS_IN_NODE=.*/N8N_BLOCK_ENV_ACCESS_IN_NODE=false/' .env
else
  echo 'N8N_BLOCK_ENV_ACCESS_IN_NODE=false' >> .env
fi

# Remove duplicate BLOCK lines (common cause of weird behavior)
awk '!seen[$0]++ || !/^N8N_BLOCK_ENV_ACCESS_IN_NODE=/' .env > .env.tmp && mv .env.tmp .env

if ! grep -q 'N8N_BLOCK_ENV_ACCESS_IN_NODE=false' "$COMPOSE_FILE"; then
  echo "Patching $COMPOSE_FILE ..."
  sed -i '/N8N_DIAGNOSTICS_ENABLED=false/a\      - N8N_BLOCK_ENV_ACCESS_IN_NODE=false' "$COMPOSE_FILE"
fi

if ! grep -q 'N8N_WEBHOOK_SECRET=\${N8N_WEBHOOK_SECRET}' "$COMPOSE_FILE"; then
  echo "WARNING: copy latest docker-compose.micro.yml from repo (missing secret passthrough lines)"
fi

# Use 2.x to match Postgres schema; never downgrade to 1.97.x after 2.x migrations
if grep -qE 'n8n:(latest|1\.97)' "$COMPOSE_FILE"; then
  sed -i 's|docker.n8n.io/n8nio/n8n:.*|docker.n8n.io/n8nio/n8n:2.20.9|' "$COMPOSE_FILE"
fi

echo "Pulling image and recreating n8n..."
docker compose -f "$COMPOSE_FILE" pull n8n
docker compose -f "$COMPOSE_FILE" up -d --force-recreate n8n
sleep 15

echo "--- Must show BLOCK=false and secrets set ---"
docker exec bexo-n8n sh -c '
  echo "n8n version: $(n8n --version 2>/dev/null || echo unknown)"
  echo "BLOCK=$N8N_BLOCK_ENV_ACCESS_IN_NODE"
  test "$N8N_BLOCK_ENV_ACCESS_IN_NODE" = "false" && echo "BLOCK OK" || echo "BLOCK BAD — fix compose/.env"
  test -n "$N8N_WEBHOOK_SECRET" && echo "WEBHOOK_SECRET OK (${#N8N_WEBHOOK_SECRET} chars)" || echo "WEBHOOK_SECRET MISSING"
'

echo "Re-test webhook from your Mac when BLOCK OK."
