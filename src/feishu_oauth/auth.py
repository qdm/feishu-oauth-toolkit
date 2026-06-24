"""OAuth 2.0 helpers: build URL, exchange code, refresh token.

Feishu endpoints used:
    - GET  https://open.feishu.cn/open-apis/authen/v1/index
    - POST https://open.feishu.cn/open-apis/authen/v2/oauth/token
"""

from __future__ import annotations

import json
import sys
import urllib.error
import urllib.parse
import urllib.request
from typing import Any

from .config import FeishuConfig, load_config


AUTH_URL = "https://open.feishu.cn/open-apis/authen/v1/index"
TOKEN_URL = "https://open.feishu.cn/open-apis/authen/v2/oauth/token"

# Default scope set used by the verification flow.
# Includes 7 read scopes + drive:drive:readonly (needed for /drive/v1/files)
# + offline_access (needed for refresh_token to be returned).
DEFAULT_SCOPES = [
    "drive:drive.search:readonly",
    "drive:drive.metadata:readonly",
    "drive:file:readonly",
    "docs:document.content:read",
    "docs:document.media:download",
    "docx:document:readonly",
    "wiki:wiki:readonly",
    "search:docs:read",
    "drive:drive:readonly",
    "offline_access",
]


def http_post(url: str, payload: dict[str, Any], timeout: float = 15.0) -> dict[str, Any]:
    """POST JSON. 4xx/5xx responses are returned with `_http_error` set instead of raising."""
    req = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json; charset=utf-8"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return json.loads(r.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        try:
            body = e.read().decode("utf-8")
        except Exception:
            body = "<empty>"
        return {"_http_error": True, "_http_status": e.code, "_http_body": body}


def build_auth_url(
    app_id: str,
    redirect_uri: str,
    scopes: list[str] | None = None,
    state: str = "feishu-oauth-state",
    prompt: str = "consent",
) -> str:
    """Build the user-facing authorization URL.

    `prompt=consent` forces the consent screen on every visit, which is what
    you want during verification.
    """
    params = {
        "app_id": app_id,
        "redirect_uri": redirect_uri,
        "scope": " ".join(scopes or DEFAULT_SCOPES),
        "state": state,
    }
    if prompt:
        params["prompt"] = prompt
    return f"{AUTH_URL}?{urllib.parse.urlencode(params)}"


def exchange_code(
    cfg: FeishuConfig,
    code: str,
    redirect_uri: str,
) -> dict[str, Any]:
    """Exchange authorization code for access_token (and refresh_token if offline_access granted)."""
    payload = {
        "grant_type": "authorization_code",
        "client_id": cfg.app_id,
        "client_secret": cfg.app_secret,
        "code": code,
        "redirect_uri": redirect_uri,
    }
    return http_post(TOKEN_URL, payload)


def refresh(cfg: FeishuConfig, refresh_token: str) -> dict[str, Any]:
    """Use a refresh_token to mint a new access_token."""
    payload = {
        "grant_type": "refresh_token",
        "client_id": cfg.app_id,
        "client_secret": cfg.app_secret,
        "refresh_token": refresh_token,
    }
    return http_post(TOKEN_URL, payload)


def save_token(resp: dict[str, Any], target: "Path | None" = None) -> "Path":
    """Persist token response JSON to disk, chmod 600."""
    import time
    from pathlib import Path

    target = target or Path.cwd() / "feishu-user-tokens.json"
    payload = dict(resp)
    payload["_issued_at"] = int(time.time())
    payload["_expires_at"] = int(time.time()) + resp.get("expires_in", 7200)
    if resp.get("refresh_token_expires_in"):
        payload["_refresh_expires_at"] = int(time.time()) + resp["refresh_token_expires_in"]
    target.write_text(json.dumps(payload, indent=2, ensure_ascii=False))
    target.chmod(0o600)
    return target


# --- CLI entry points --------------------------------------------------------


def cli_build_url() -> None:
    cfg = load_config()
    redirect = sys.argv[1] if len(sys.argv) > 1 else input("redirect_uri: ").strip()
    print(build_auth_url(cfg.app_id, redirect))


if __name__ == "__main__":
    cli_build_url()
