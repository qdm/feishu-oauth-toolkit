#!/usr/bin/env bash
# Install cloudflared (if missing) and enable the systemd --user quick-tunnel service.
#
# Run once. After this, `tunnel-url` will print the current public URL.
set -euo pipefail

USER_BIN="$HOME/.local/bin/cloudflared"
UNIT_DIR="$HOME/.config/systemd/user"
UNIT_FILE="$UNIT_DIR/quick-tunnel.service"

if ! command -v cloudflared >/dev/null 2>&1 && [[ ! -x "$USER_BIN" ]]; then
  echo ">>> installing cloudflared to $USER_BIN"
  mkdir -p "$HOME/.local/bin"
  curl -fsSL -o /tmp/cloudflared \
    https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64
  install -m 0755 /tmp/cloudflared "$USER_BIN"
  rm /tmp/cloudflared
fi

# Make sure ~/.local/bin is on PATH for systemd --user
grep -qxF 'export PATH="$HOME/.local/bin:$PATH"' ~/.bashrc 2>/dev/null \
  || echo 'export PATH="$HOME/.local/bin:$PATH"' >> ~/.bashrc

mkdir -p "$UNIT_DIR"
cat > "$UNIT_FILE" <<'EOF'
[Unit]
Description=Cloudflare Quick Tunnel to localhost:18080 (Feishu OAuth callback)
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
Environment=PATH=/home/agentuser/.local/bin:/usr/local/bin:/usr/bin:/bin
ExecStart=/home/agentuser/.local/bin/cloudflared tunnel --no-autoupdate --url http://localhost:18080
Restart=always
RestartSec=5
StandardOutput=journal
StandardError=journal
KillMode=mixed
TimeoutStopSec=15

[Install]
WantedBy=default.target
EOF
# NOTE: replace the hard-coded /home/agentuser path above with $HOME if you copy this
# script to a different machine. We pin it here so the unit file is identical across
# restarts on the same host.

systemctl --user daemon-reload
systemctl --user enable --now quick-tunnel.service

echo ""
echo ">>> waiting 8s for tunnel to register..."
sleep 8
echo ""
echo ">>> tunnel URL (changes every restart — paste this into Feishu backend):"
"$USER_BIN" --version
echo ""
echo ">>> run scripts/tunnel-url.sh to print the current public URL anytime"
