#!/usr/bin/env bash
# Optional: install upstream design skills into .claude/skills (dev machine).
# Production Docker image uses bundled skills/ copied to .claude/skills/.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
mkdir -p .claude/skills

echo "Bundled BEXO skills (always used in Cloud Run):"
ls -1 skills/

if [[ -x "$(dirname "$0")/sync-skills-from-bexo.sh" ]]; then
  echo "Syncing premium skills from BEXO/.agents/skills ..."
  "$(dirname "$0")/sync-skills-from-bexo.sh" || true
fi

if command -v npx >/dev/null 2>&1; then
  echo "Installing optional upstream skills (requires network)..."
  npx skills add Leonxlnx/taste-skill --yes 2>/dev/null || true
  npx skills add pbakaus/impeccable --skill impeccable --yes 2>/dev/null || true
  npx skills add nextlevelbuilder/ui-ux-pro-max-skill --yes 2>/dev/null || true
  npx skills add kylezantos/design-motion-principles --skill design-motion-principles --yes 2>/dev/null || true
  npx skills add vercel-labs/agent-skills --skill web-design-guidelines --yes 2>/dev/null || true
fi

cp -R skills/* .claude/skills/ 2>/dev/null || true
echo "Done. Claude Code reads .claude/skills/ and .claude/CLAUDE.md"
