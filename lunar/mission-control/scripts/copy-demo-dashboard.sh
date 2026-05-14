#!/usr/bin/env bash
# Copy mission-control (without node_modules) for an isolated demo tree — e.g. second repo checkout on a laptop.
set -euo pipefail
MC_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DEST="${1:-${HOME}/mission-control-demo}"
mkdir -p "${DEST}"
rsync -a \
  --delete \
  --exclude node_modules \
  --exclude dist \
  --exclude .vite \
  "${MC_DIR}/" "${DEST}/"
echo "Copied mission-control -> ${DEST}"
echo "Next: cd \"${DEST}\" && pnpm install && pnpm dev:demo"
echo "Then open http://\$(tailscale ip -4):5173 from your phone (same tailnet) or use Tailscale Serve (see lunar/mission-control/README.md)."
