#!/usr/bin/env bash
# Enable the systemd --user oauth-server service (Python HTTP server on :18080).
set -euo pipefail

UNIT_DIR="$HOME/.config/systemd/user"
UNIT_FILE="$UNIT_DIR/oauth-server.service"
SCRIPT_PATH="$HOME/feishu-oauth-toolkit-build/src/feishu_oauth/server.py"

mkdir -p "$UNIT_DIR"
cat > "$UNIT_FILE" <<EOF
[Unit]
Description=Feishu OAuth callback server (Python http.server, 127.0.0.1:18080)
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
Environment=PATH=$HOME/.local/bin:/usr/local/bin:/usr/bin:/bin
ExecStart=/usr/bin/python3 $SCRIPT_PATH
Restart=always
RestartSec=3
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=default.target
EOF

systemctl --user daemon-reload
systemctl --user enable --now oauth-server.service
sleep 1
curl -sS http://127.0.0.1:18080/health && echo " — oauth-server is up"
