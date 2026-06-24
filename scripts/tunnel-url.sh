#!/usr/bin/env bash
# Print the current cloudflared quick-tunnel URL.
# Reads the most recent `https://*.trycloudflare.com` from the user journal,
# and health-checks it before printing.
set -euo pipefail

CACHE="${TMPDIR:-/tmp}/quick-tunnel.url"
URL=$(journalctl --user -u quick-tunnel.service --no-pager -n 200 2>/dev/null \
  | grep -oE 'https://[a-z0-9-]+\.trycloudflare\.com' \
  | tail -n1 || true)

if [[ -z "${URL:-}" && -s "$CACHE" ]]; then
  URL=$(cat "$CACHE")
fi

if [[ -n "${URL:-}" ]]; then
  code=$(curl -sS -o /dev/null -w '%{http_code}' --max-time 8 "$URL/" 2>/dev/null || echo "000")
  if [[ "$code" =~ ^[2345] ]]; then
    echo "$URL" > "$CACHE"
    echo "$URL"
    exit 0
  fi
fi

echo "ERR: no live trycloudflare URL for quick-tunnel.service" >&2
echo "  - systemctl --user status quick-tunnel" >&2
echo "  - journalctl --user -u quick-tunnel -n 50" >&2
exit 1
