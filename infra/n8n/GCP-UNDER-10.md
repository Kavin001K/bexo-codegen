# n8n on GCP for under $10/month

## Recommended setup

| Choice | Monthly cost |
|--------|----------------|
| **e2-micro** VM (us-central1) | ~$6–7 compute |
| 20–30 GB disk | Often covered by free tier |
| n8n + Postgres on same VM (Docker) | $0 extra |
| No Redis / no worker | Saves RAM & money |
| nginx + Let's Encrypt on VM | $0 |

**Total: ~$6–9/month** (under $10)

Avoid **e2-small** (~$13+) and **Render** (~$14 with Postgres).

## Free tier (may be $0)

New GCP accounts get **1× e2-micro** free per month in `us-central1`, `us-west1`, or `us-east1`.

Check: https://cloud.google.com/free

If you already use the free e2-micro elsewhere, you'll pay ~$6/mo for a second one.

## What we remove vs full VM plan

| Removed | Why |
|---------|-----|
| n8n-worker | Saves ~256MB RAM |
| Redis + queue mode | Not needed at low volume |
| e2-small | Too expensive |

Use `docker-compose.micro.yml` instead of `docker-compose.yml`.

## Quick deploy

```bash
# Mac — create micro VM
gcloud compute instances create bexo-n8n \
  --zone=us-central1-a \
  --machine-type=e2-micro \
  --boot-disk-size=20GB \
  --image-family=ubuntu-2204-lts \
  --image-project=ubuntu-os-cloud \
  --tags=bexo-n8n

gcloud compute firewall-rules create bexo-n8n-allow-web \
  --allow=tcp:22,tcp:80,tcp:443 \
  --target-tags=bexo-n8n

# Copy files
gcloud compute scp --recurse infra/n8n bexo-n8n:~/bexo-n8n --zone=us-central1-a

# SSH
gcloud compute ssh bexo-n8n --zone=us-central1-a
```

On VM:

```bash
# Install Docker (see main build guide Phase 2)
cd ~/bexo-n8n
cp .env.example .env
nano .env   # set passwords + WEBHOOK_URL

docker compose -f docker-compose.micro.yml up -d
# nginx + certbot for HTTPS (same as full guide)
```

## If VM feels slow

Upgrade only the machine type (keeps disk & IP):

```bash
gcloud compute instances stop bexo-n8n --zone=us-central1-a
gcloud compute instances set-machine-type bexo-n8n \
  --zone=us-central1-a --machine-type=e2-small
gcloud compute instances start bexo-n8n --zone=us-central1-a
```

That moves you to ~$13/mo when you have more users.
