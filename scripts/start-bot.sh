#!/usr/bin/env bash
# 装/起 feishu-bot systemd --user service
# 前置: ~/.feishu-bot-venv 存在(里头装了 lark-oapi), .env 写在 WorkingDirectory 里
set -euo pipefail

UNIT_DIR="$HOME/.config/systemd/user"
UNIT_FILE="$UNIT_DIR/feishu-bot.service"
SCRIPT_UNIT="$HOME/feishu-oauth-toolkit-build/scripts/systemd/feishu-bot.service"

if [[ ! -d "$HOME/.feishu-bot-venv" ]]; then
  echo "❌ 缺少 venv: ~/.feishu-bot-venv (lark-oapi 装在里头)"
  echo "   创建:"
  echo "     uv venv ~/.feishu-bot-venv --python 3.11"
  echo "     source ~/.feishu-bot-venv/bin/activate"
  echo "     pip install lark-oapi"
  exit 1
fi

# 复制 unit 到 ~/.config/systemd/user/(systemd 只认这里)
mkdir -p "$UNIT_DIR"
cp -f "$SCRIPT_UNIT" "$UNIT_FILE"

systemctl --user daemon-reload
systemctl --user enable --now feishu-bot.service
sleep 3
echo
echo "--- 状态 ---"
systemctl --user --no-pager status feishu-bot.service | head -15
echo
echo "--- 实时日志(看 WS 连接 + bot identity) ---"
journalctl --user -u feishu-bot.service --no-pager -n 10
