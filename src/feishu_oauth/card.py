"""飞书卡片 JSON 模板常量 — 纯数据,不含任何 SDK 依赖,易测试.

卡片遵循飞书卡片 schema 2.0:顶层 header / body.elements / actions。
按钮用 tag="button" + behaviors=[{type:"open_url", default_url:..., url_target:...}]。
"""

from __future__ import annotations

from typing import Any

# 卡片右上角的浅灰色小字提示(模板标签,可被调用方替换)
TAG_PLEASE_BROWSER = "请在浏览器中完成"
TAG_DONE_BRIEF = "授权完成"


def _card_skeleton(header_title: str) -> dict[str, Any]:
    """返回一张空卡片的骨架(header + 空 elements)。

    飞书卡片 schema 2.0 中 header 只认 title 和 template 两个字段,不认 tag。
    """
    return {
        "schema": "2.0",
        "header": {
            "title": {
                "tag": "plain_text",
                "content": header_title,
            },
            "template": "blue",
        },
        "body": {
            "elements": [],
        },
    }


def auth_request_card(auth_url: str) -> dict[str, Any]:
    """生成「请求用户授权」卡片。

    参数:
        auth_url: feishu_oauth.auth.build_auth_url(...) 拼出的绝对 HTTPS 授权 URL
                  必须以 https:// 开头(飞书只允许公网 https URL)。
    """
    if not auth_url.startswith("https://"):
        raise ValueError(
            f"auth_url 必须是绝对 https URL,收到:{auth_url[:60]!r}..."
        )

    card = _card_skeleton("🔐 飞书 OAuth 授权")
    button = {
        "tag": "button",
        "text": {
            "tag": "plain_text",
            "content": "👉 同意并授权",
        },
        "type": "primary",
        "url": auth_url,
    }
    card["body"]["elements"] = [
        {
            "tag": "div",
            "text": {
                "tag": "lark_md",
                "content": (
                    "机器人需要读取你的云空间(文档 / Wiki / 文件元信息),"
                    "请在浏览器中点同意完成授权。\n\n"
                    "授权完成后,机器人将获得你的 **user_access_token**,"
                    "可用于调用飞书 OpenAPI。"
                ),
            },
        },
        {"tag": "hr"},
        button,
    ]
    return card


def auth_done_card(
    access_token_minutes_left: int | None,
    refresh_token_days_left: int | None,
) -> dict[str, Any]:
    """生成「授权完成 / 当前 token 状态」确认卡片。

    参数:
        access_token_minutes_left: user_access_token 还有几分钟过期;None 表示不可用
        refresh_token_days_left:   refresh_token 还有几天过期;None 表示没有 refresh_token
    """
    if access_token_minutes_left is None:
        at_line = "你的 **access_token** 当前不可用(尚未授权或已过期)。"
    else:
        at_line = f"你的 **access_token** 还有 **{access_token_minutes_left}** 分钟过期。"

    if refresh_token_days_left is None:
        rt_line = "没有可用的 **refresh_token**(可能没勾选 `offline_access`)。"
    else:
        rt_line = f"**refresh_token** 还有 **{refresh_token_days_left}** 天过期。"

    card = _card_skeleton("✅ 授权完成")
    card["header"]["template"] = "green"
    card["body"]["elements"] = [
        {
            "tag": "div",
            "text": {
                "tag": "lark_md",
                "content": (
                    f"{at_line}\n\n{rt_line}\n\n"
                    "需要重新授权时,随时给机器人发 `/auth` 即可。"
                ),
            },
        },
    ]
    return card