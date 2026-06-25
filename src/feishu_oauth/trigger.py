"""业务触发逻辑 — 纯函数,无 SDK 依赖,易单测。

输入:用户消息文本 + 当前是否有有效 user_access_token
输出:应该发给用户的卡片 JSON dict,或 None(机器人沉默,不打扰)

设计原则:
- 所有 IO/凭据/构建 URL 的活都交给 bot.py(它在调用本模块前准备好)
- 本模块只做字符串匹配 + 选模板,绝对保证可单测、可 mock
"""

from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any

from .auth import build_auth_url
from .card import auth_done_card, auth_request_card


# 触发关键词 / 命令:机器人收到这些消息才会回复
# 用户可以发: /auth, 帮我授权, 我要auth, 等
_TRIGGER_KEYWORDS = ("授权", "auth")


def _is_trigger(message: str) -> bool:
    """判断用户消息是否触发了 OAuth 卡片。

    规则(任一命中即触发):
      - 精确等于 "/auth"(忽略大小写、忽略首尾空白)
      - 包含中文 "授权"
      - 包含英文 "auth"(大小写不敏感)
    """
    if not message:
        return False
    stripped = message.strip()
    if stripped.lower() == "/auth":
        return True
    if "授权" in stripped:
        return True
    if "auth" in stripped.lower():
        return True
    return False


def _read_token_file(token_file: Path) -> dict[str, Any] | None:
    """读 token 文件,失败返回 None(不抛异常)。"""
    try:
        if not token_file.exists():
            return None
        return json.loads(token_file.read_text(encoding="utf-8"))
    except Exception:
        return None


def compute_token_expiry(
    token_file: Path | None = None,
) -> tuple[int | None, int | None]:
    """从磁盘 token 文件计算 (access_token 还剩几分钟, refresh_token 还剩几天)。

    返回 (None, None) 表示无文件或无法解析。
    """
    path = token_file or (Path.cwd() / "feishu-user-tokens.json")
    data = _read_token_file(path)
    if not data:
        return None, None
    now = int(time.time())

    # access_token 剩余分钟数
    exp_at = data.get("_expires_at")
    at_min: int | None = None
    if isinstance(exp_at, (int, float)) and exp_at > now:
        at_min = max(0, int((exp_at - now) // 60))

    # refresh_token 剩余天数
    refresh_exp = data.get("_refresh_expires_at")
    rt_days: int | None = None
    if isinstance(refresh_exp, (int, float)) and refresh_exp > now:
        rt_days = max(0, int((refresh_exp - now) // 86400))

    return at_min, rt_days


def decide_response(
    user_message: str,
    has_valid_token: bool,
    redirect_uri: str,
    app_id: str | None = None,
    state: str = "feishu-bot-trigger",
) -> dict[str, Any] | None:
    """根据用户消息 + 当前 token 状态,返回要发的卡片 JSON,或 None(沉默)。

    参数:
        user_message:    用户在飞书里发的纯文本(机器人已经剥离过 @ 等前缀)
        has_valid_token: 调用方判断"磁盘上 user_access_token 是否还有效"
        redirect_uri:    OAuth 回调地址(必须与飞书后台配置一致,绝对 https)
        app_id:          飞书 App ID(用于拼 auth URL),可选 — 不传则用占位,
                         bot.py 会在 send 前用真实值 replace(向后兼容)
        state:           OAuth state 参数,防 CSRF

    返回:
        dict: 一张卡片 JSON(可直接发给 im.message.create)
        None: 机器人不应回复(默认沉默,不打扰)
    """
    if not _is_trigger(user_message):
        return None

    if has_valid_token:
        at_min, rt_days = compute_token_expiry()
        return auth_done_card(at_min, rt_days)

    # 没 token → 发授权请求卡片
    # bot.py 必须传 app_id,否则用占位符(老路径,向后兼容)
    auth_url = build_auth_url(
        app_id=app_id or "__APP_ID_PLACEHOLDER__",
        redirect_uri=redirect_uri,
        state=state,
    )
    return auth_request_card(auth_url)
