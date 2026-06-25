"""End-to-end verification: read code → exchange → probe scopes → refresh."""

from __future__ import annotations

import json
import sys
import urllib.error
import urllib.parse
import urllib.request
from typing import Any

from feishu_oauth.auth import exchange_code, refresh, save_token
from feishu_oauth.config import load_config


def http_get(url: str, headers: dict[str, str] | None = None, timeout: float = 15.0) -> dict[str, Any]:
    req = urllib.request.Request(url, headers=headers or {}, method="GET")
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return json.loads(r.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        try:
            body = e.read().decode("utf-8")
        except Exception:
            body = "<empty>"
        return {"_http_error": True, "_http_status": e.code, "_http_body": body}


def hr(title: str) -> None:
    print(f"\n{'=' * 60}\n  {title}\n{'=' * 60}")


def step_exchange(cfg, code: str, redirect_uri: str) -> dict[str, Any]:
    hr("Step 1: code → user_access_token")
    print(f"  client_id:    {cfg.app_id}")
    print(f"  redirect_uri: {redirect_uri}")

    resp = exchange_code(cfg, code, redirect_uri)
    if resp.get("_http_error"):
        print(f"  ❌ HTTP {resp['_http_status']}: {resp['_http_body']}")
        if "20004" in resp.get("_http_body", ""):
            print("     👉 code 已过期(5 分钟),重新走授权")
        elif "20003" in resp.get("_http_body", ""):
            print("     👉 code 已被使用(只能一次),重新走授权")
        elif "20023" in resp.get("_http_body", ""):
            print("     👉 redirect_uri 与后台配置不一致")
        elif "20027" in resp.get("_http_body", ""):
            print("     👉 scope 未申请或未发布")
        sys.exit(1)

    if resp.get("code", 0) != 0:
        print(f"  ❌ 失败: code={resp.get('code')}, msg={resp.get('msg')}")
        sys.exit(1)

    print(f"  ✅ access_token  长度: {len(resp.get('access_token', ''))}")
    print(f"     expires_in:   {resp.get('expires_in')} 秒 (≈ {resp.get('expires_in', 0) // 60} 分钟)")
    print(f"     refresh_token 长度: {len(resp.get('refresh_token', ''))}")
    print(f"     scope:        {resp.get('scope')}")
    return resp


def step_search(user_access_token: str) -> None:
    hr("Step 2: 搜索端点探活")
    endpoints = [
        ("/drive/v1/files", "https://open.feishu.cn/open-apis/drive/v1/files?page_size=10"),
        ("/drive/v1/files?folder=root", "https://open.feishu.cn/open-apis/drive/v1/files?folder=root&page_size=10"),
    ]
    h = {"Authorization": f"Bearer {user_access_token}"}
    for name, url in endpoints:
        print(f"\n  → {name}")
        resp = http_get(url, headers=h)
        if resp.get("_http_error"):
            print(f"     ❌ HTTP {resp['_http_status']}: {resp['_http_body'][:200]}")
        elif resp.get("code", 0) == 0:
            files = resp.get("data", {}).get("files", [])
            print(f"     ✅ code=0, items={len(files)}")
            for i, f in enumerate(files[:3], 1):
                print(f"       [{i}] {f.get('name')}  type={f.get('type')}  token={f.get('token', '')[:24]}...")
        else:
            print(f"     ⚠️ code={resp.get('code')}, msg={resp.get('msg')}")


def step_refresh(cfg, refresh_token: str | None) -> dict[str, Any] | None:
    hr("Step 3: refresh_token → 新 access_token")
    if not refresh_token:
        print("  ⏭️  跳过: 本次响应里没有 refresh_token(没加 offline_access scope)")
        return None
    resp = refresh(cfg, refresh_token)
    if resp.get("_http_error"):
        print(f"  ❌ HTTP {resp['_http_status']}: {resp['_http_body']}")
        return None
    if resp.get("code", 0) == 0:
        print(f"  ✅ 新 access_token 长度: {len(resp.get('access_token', ''))}")
        print(f"     新 refresh_token 长度: {len(resp.get('refresh_token', ''))}")
        return resp
    print(f"  ❌ 失败: code={resp.get('code')}, msg={resp.get('msg')}")
    return None


def cli_main() -> None:
    cfg = load_config()

    # Step 0: read the code
    if not cfg.code_file.exists():
        print(f"❌ 找不到 {cfg.code_file}")
        print("   请先打开授权 URL 完成飞书授权")
        sys.exit(1)
    code = json.loads(cfg.code_file.read_text())["code"]
    print(f"[INFO] code 长度 {len(code)}")

    # redirect_uri 走命令行参数(默认: 让你手动确认)
    redirect_uri = sys.argv[1] if len(sys.argv) > 1 else input("redirect_uri: ").strip()

    tokens = step_exchange(cfg, code, redirect_uri)
    save_token(tokens, cfg.token_file)
    print(f"  → token 已存: {cfg.token_file}")

    step_search(tokens["access_token"])
    new_tokens = step_refresh(cfg, tokens.get("refresh_token", ""))
    if new_tokens:
        save_token(new_tokens, cfg.token_file)
        print(f"  → 新 token 已覆盖: {cfg.token_file}")

    print(f"\n{'=' * 60}\n  完成 ✅\n{'=' * 60}")


if __name__ == "__main__":
    cli_main()
