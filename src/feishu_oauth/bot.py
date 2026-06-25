"""飞书机器人入口 — WebSocket 长连接,响应 im.message.receive_v1 事件。

架构:
    用户在飞书发消息 → 飞书 Open Platform → WS 推送 → FeishuChannel.on("message") →
    本文件 _on_message() → trigger.decide_response() → channel.send(card) → 用户收到卡片

凭据(全部从环境变量读,绝不写死):
    FEISHU_APP_ID        — 应用 App ID (cli_xxx)
    FEISHU_APP_SECRET    — 应用 App Secret
    FEISHU_REDIRECT_URI  — OAuth 回调地址(必须与飞书后台配置一致,绝对 https)
    FEISHU_BOT_LOG_LEVEL — 可选,默认 INFO
"""

from __future__ import annotations

import asyncio
import json
import os
import sys
from pathlib import Path

from lark_oapi.channel import FeishuChannel  # type: ignore[import-not-found]

from . import __version__
from .config import load_config
from .trigger import compute_token_expiry, decide_response


def _read_env(name: str, default: str | None = None, required: bool = False) -> str:
    """读环境变量,缺失且 required 时给出友好报错。"""
    v = os.environ.get(name, "").strip() or default
    if required and not v:
        raise SystemExit(
            f"❌ 缺少环境变量 {name}\n"
            f"   export {name}=...\n"
            f"   或者把它写进 .env(本仓库不会 commit .env)"
        )
    return v or ""


def _has_valid_token() -> bool:
    """检查磁盘上的 user_access_token 是否还有效(粗略判断,>=1 分钟剩余)。"""
    at_min, _ = compute_token_expiry()
    return at_min is not None and at_min >= 1


def _extract_text(message: str | None) -> str:
    """把飞书 IM 消息 JSON 字符串里的纯文本抠出来,失败返回空串。

    飞书 IM 消息是字符串化的 JSON:
      - text 类型: {"text": "hello"}
      - post 类型: {"title":..., "content":[[{"tag":"text","text":"..."}]]}
    """
    if not message:
        return ""
    try:
        obj = json.loads(message)
    except Exception:
        return ""

    if isinstance(obj, dict):
        if "text" in obj and isinstance(obj["text"], str):
            return obj["text"]
        if "content" in obj and isinstance(obj["content"], list):
            chunks: list[str] = []
            for line in obj["content"]:
                if isinstance(line, list):
                    for node in line:
                        if isinstance(node, dict) and node.get("tag") == "text":
                            chunks.append(str(node.get("text", "")))
            return "".join(chunks)
    return ""


async def _on_message(channel: FeishuChannel, inbound) -> None:
    """处理单条入站消息。"""
    try:
        text = inbound.content_text or ""
        sender_id = inbound.sender_id or ""
        chat_id = inbound.chat_id or ""
        message_id = inbound.message_id or ""

        sys.stderr.write(
            f"[bot] recv msg from={sender_id} chat={chat_id} text={text!r}\n"
        )

        cfg = load_config()
        redirect_uri = _read_env("FEISHU_REDIRECT_URI", required=True)
        card = decide_response(
            user_message=text,
            has_valid_token=_has_valid_token(),
            redirect_uri=redirect_uri,
            app_id=cfg.app_id,
        )
        if card is None:
            # 机器人沉默,不打扰
            return

        # 把卡片发回当前聊天 / 用户
        target = chat_id or sender_id
        result = await channel.send(
            to=target,
            message={"card": card},
            opts={"reply_to": message_id} if message_id else None,
        )
        if not result.success:
            err = result.error
            # lark-oapi 1.6 的 SendError 用 hint / raw_code / code / retryable,没有 msg 属性
            sys.stderr.write(
                f"[bot] send failed: code={err.raw_code if err else '?'} "
                f"hint={err.hint if err else '?'}\n"
            )
    except Exception as exc:  # pragma: no cover — 保护 handler,不让 SDK 整个崩
        sys.stderr.write(f"[bot] _on_message exception: {exc!r}\n")


def build_channel() -> FeishuChannel:
    """构造 FeishuChannel(WS 模式),注册 message 事件 handler。"""
    cfg = load_config()

    channel = FeishuChannel(
        app_id=cfg.app_id,
        app_secret=cfg.app_secret,
    )

    # 注册 im.message.receive_v1(在 channel 层用别名 "message")
    def _sync_handler(inbound) -> None:
        # inbound 是 SDK 已 normalize 的对象,直接丢给 async handler
        asyncio.create_task(_on_message(channel, inbound))

    channel.on("message", _sync_handler)

    # 也监听 error / reconnecting,方便排查
    def _on_error(err) -> None:
        sys.stderr.write(f"[bot] channel error: {err!r}\n")

    def _on_reconnecting() -> None:
        sys.stderr.write("[bot] WS reconnecting...\n")

    def _on_reconnected() -> None:
        sys.stderr.write("[bot] WS reconnected.\n")

    channel.on("error", _on_error)
    channel.on("reconnecting", _on_reconnecting)
    channel.on("reconnected", _on_reconnected)

    return channel


def main() -> None:
    """CLI 入口:`python -m feishu_oauth.bot` / `feishu-bot`."""
    sys.stderr.write(
        f"[bot] feishu-oauth-toolkit-bot v{__version__} starting\n"
        f"[bot] pid={os.getpid()} cwd={Path.cwd()}\n"
    )

    # 启动前先确保 redirect_uri 已设置,否则立刻报错
    _read_env("FEISHU_REDIRECT_URI", required=True)
    # load_config 会校验 app_id/secret,提前调一次让错误更早暴露
    load_config()

    channel = build_channel()
    sys.stderr.write("[bot] connecting WS...\n")
    try:
        channel.start()
    except KeyboardInterrupt:
        sys.stderr.write("[bot] KeyboardInterrupt, stopping...\n")
        channel.stop()


if __name__ == "__main__":
    main()