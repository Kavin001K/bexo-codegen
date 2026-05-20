#!/usr/bin/env bash
# Run ON the n8n VM: bash recover-n8n.sh
# Fixes "Database is not ready" (503) and restarts stack in the right order.
set -euo pipefail

cd "$(dirname "$0")"
COMPOSE="docker compose -f docker-compose.micro.yml"

if [[ ! -f .env ]]; then
  echo "ERROR: ~/bexo-n8n/.env missing. Copy from .env.example first."
  exit 1
fi

# shellcheck disable=SC1091
source .env

if [[ -z "${DB_PASSWORD:-}" ]]; then
  echo "ERROR: DB_PASSWORD is empty in .env"
  exit 1
fi

if [[ -z "${N8N_ENCRYPTION_KEY:-}" ]]; then
  echo "ERROR: N8N_ENCRYPTION_KEY is empty in .env (required if n8n was used before)"
  exit 1
fi

echo "==> Ensuring swap (helps e2-micro during n8n DB migrations)"
if ! swapon --show | grep -q '/swapfile'; then
  sudo fallocate -l 1G /swapfile 2>/dev/null || sudo dd if=/dev/zero of=/swapfile bs=1M count=1024 status=progress
  sudo chmod 600 /swapfile
  sudo mkswap /swapfile
  sudo swapon /swapfile
  grep -q '/swapfile' /etc/fstab || echo '/swapfile none swap sw 0 0' | sudo tee -a /etc/fstab
fi

echo "==> Stopping stack (keeps volumes — workflows preserved)"
$COMPOSE down

echo "==> Starting Postgres only"
$COMPOSE up -d postgres

echo "==> Waiting for Postgres (up to 90s)"
for i in $(seq 1 18); do
  if $COMPOSE exec -T postgres pg_isready -U n8n -d n8n >/dev/null 2>&1; then
    echo "    Postgres ready (${i}0s)"
    break
  fi
  sleep 5
done

echo "==> Testing DB password from .env"
if ! PGPASSWORD="$DB_PASSWORD" $COMPOSE exec -T -e PGPASSWORD postgres \
  psql -U n8n -d n8n -c 'SELECT 1 AS ok;' >/dev/null 2>&1; then
  echo ""
  echo "FATAL: DB_PASSWORD in .env does NOT match the Postgres volume."
  echo "  Do NOT change DB_PASSWORD after first install unless you reset the DB."
  echo "  Fix: set DB_PASSWORD in .env to the ORIGINAL value, OR (last resort, loses n8n DB):"
  echo "    docker compose -f docker-compose.micro.yml down -v"
  echo "    # then fix .env and run this script again"
  exit 1
fi
echo "    DB password OK"

echo "==> Starting n8n"
$COMPOSE up -d n8n

echo "==> Waiting for n8n HTTP (up to 3 min on e2-micro)"
n8n_ok=0
for i in $(seq 1 36); do
  if curl -sf -o /dev/null -u "${N8N_BASIC_AUTH_USER:-admin}:${N8N_PASSWORD}" \
    "http://127.0.0.1:5678/healthz" 2>/dev/null; then
    echo "    n8n ready (~$((i * 5))s)"
    n8n_ok=1
    break
  fi
  sleep 5
done
if [[ "$n8n_ok" -ne 1 ]]; then
  echo "WARN: n8n /healthz not up yet — check: docker logs bexo-n8n --tail 80"
fi

echo ""
echo "==> Container status"
$COMPOSE ps

echo ""
echo "==> Last n8n log lines"
docker logs bexo-n8n --tail 15 2>&1 || true

echo ""
echo "Done. Open: https://n8n.mybexo.com/home/workflows"
echo "  (Old /workflow/XXXX bookmarks break after re-import — use Workflows list.)"
echo "If still 503, wait 2 more minutes then: docker logs bexo-n8n --tail 50"
