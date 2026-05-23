# =============================================================================
# Stage 1: Pre-install Next.js template dependencies (not uploaded to GCS)
# =============================================================================
FROM node:20-bookworm-slim AS template_deps
WORKDIR /tpl
COPY templates/portfolio-next/package.json templates/portfolio-next/package-lock.json* ./
RUN npm ci --omit=dev 2>/dev/null || npm install --omit=dev

# =============================================================================
# Stage 2: Production codegen image (Claude Code + Python + Playwright)
# =============================================================================
FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    chromium \
    chromium-driver \
    fonts-unifont \
    fonts-liberation \
    curl \
    gnupg \
    git \
    ca-certificates \
    && curl -fsSL https://deb.nodesource.com/setup_20.x | bash - \
    && apt-get install -y --no-install-recommends nodejs \
    && rm -rf /var/lib/apt/lists/*

# Claude Code CLI (required for CODEGEN_ENGINE=claude)
RUN npm install -g @anthropic-ai/claude-code@latest

ENV CHROME_PATH=/usr/bin/chromium
ENV PLAYWRIGHT_CHROMIUM_EXECUTABLE_PATH=/usr/bin/chromium
ENV HOME=/tmp
ENV CODEGEN_ENGINE=claude
ENV SKIP_CLAUDE=false
ENV NODE_OPTIONS=--max-old-space-size=3072

# LLM routing (override in Cloud Run deploy / cloudbuild)
ENV DEEPSEEK_ANTHROPIC_BASE_URL=https://api.deepseek.com/anthropic
ENV DEEPSEEK_MODEL=deepseek-v4-pro[1m]
ENV DEEPSEEK_MODEL_FAST=deepseek-v4-flash
ENV KIMI_ANTHROPIC_BASE_URL=https://openrouter.ai/api
ENV KIMI_MODEL=moonshotai/kimi-k2
ENV OPENROUTER_ANTHROPIC_BASE_URL=https://openrouter.ai/api

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt \
    && npm install -g lighthouse@12.6.0

COPY src/ ./src/
COPY prompts/ ./prompts/
COPY .claude/ ./.claude/
COPY skills/ ./.claude/skills/
COPY scripts/ ./scripts/
RUN chmod +x ./scripts/*.sh 2>/dev/null || true

# Template: source + prebuilt node_modules (no 300MB upload)
COPY templates/portfolio-next/ ./templates/portfolio-next/
COPY --from=template_deps /tpl/node_modules ./templates/portfolio-next/node_modules

ENV PYTHONPATH=/app
ENV PORT=8080
ENV RUN_LIGHTHOUSE=false

EXPOSE 8080

CMD ["python", "src/main.py"]
