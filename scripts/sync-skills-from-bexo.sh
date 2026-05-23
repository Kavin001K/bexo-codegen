#!/usr/bin/env bash
# Sync premium Claude Code skills from BEXO/.agents/skills into codegen (Docker + VM).
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
BEXO_SKILLS="${BEXO_SKILLS:-$(cd "$ROOT/../BEXO/.agents/skills" 2>/dev/null && pwd || true)}"

if [[ -z "$BEXO_SKILLS" || ! -d "$BEXO_SKILLS" ]]; then
  echo "ERROR: BEXO skills not found. Set BEXO_SKILLS to BEXO/.agents/skills"
  exit 1
fi

mkdir -p "$ROOT/skills" "$ROOT/.claude/skills"

PREMIUM=(
  imagegen-frontend-web
  image-to-code
  stitch-design-taste
  brandkit
  high-end-visual-design
  redesign-existing-projects
  minimalist-ui
  industrial-brutalist-ui
  design-taste-frontend
)

CORE=(
  frontend-design
  impeccable
  web-design-guidelines
  taste-skill
  ui-ux-pro-max
  design-motion-principles
  emil-design-eng
)

sync_one() {
  local name="$1"
  local src="$BEXO_SKILLS/$name"
  if [[ ! -d "$src" ]]; then
    echo "  skip $name (missing in BEXO)"
    return 0
  fi
  rm -rf "$ROOT/skills/$name" "$ROOT/.claude/skills/$name"
  cp -R "$src" "$ROOT/skills/$name"
  cp -R "$src" "$ROOT/.claude/skills/$name"
  echo "  synced $name"
}

echo "From: $BEXO_SKILLS"
echo "Premium:"
for s in "${PREMIUM[@]}"; do sync_one "$s"; done
echo "Core (if present in BEXO):"
for s in "${CORE[@]}"; do sync_one "$s"; done

echo "Done. $(ls -1 "$ROOT/skills" | wc -l | tr -d ' ') skills in skills/ and .claude/skills/"
