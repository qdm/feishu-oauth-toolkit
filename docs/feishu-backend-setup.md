# 飞书 (Feishu) backend setup checklist

These are the manual steps you need to complete in the Feishu developer console
**before** `feishu-verify` can succeed. Captured from a real test on
2026-06-24 against a 自建应用 named `cloud`.

If you get stuck, the symptom-to-fix table at the end maps the most common
errors to their root cause.

---

## 1. App credentials

- 飞书开放平台 → 你的应用 → 凭证与基础信息
- Copy `App ID` (looks like `cli_xxxxxxxxxxxx`) and `App Secret` into `.env`:
  ```
  FEISHU_APP_ID=cli_xxxxxxxxxxxx
  FEISHU_APP_SECRET=your-secret
  ```

---

## 2. Enable the "网页应用" capability — **and fill the 主页 URL**

This is the step that blocks most first-time setups.

- 应用详情 → **应用能力** → 添加能力 → 选 **网页应用**
- ⚠️ This is **mandatory**: without it, the OAuth redirect-URL field in
  安全设置 simply does not appear. OAuth flow will fail with `20023` at
  consent time.

### 🪤 The 主页 URL 陷阱

Once you add the Web App capability, the form will ask for a **桌面端主页**
and **移动端主页** URL. These are **not** used by the OAuth flow, but the
form **will not save** without them.

For a pure headless CLI you don't need a real product page. Pick a placeholder:

- `https://example.com` (any real-looking URL)
- `https://github.com/qdm/feishu-oauth-toolkit` (this repo, harmless)

> Both will satisfy the form. The OAuth redirect URL (configured in
> [step 4](#4-configure-the-redirect-url) below) is what actually gets used
> during the authorization flow.

---

## 3. Apply for 9 read scopes + `offline_access`

In **权限管理**, search for and apply for each of these:

| Scope                          | Description                              |
|--------------------------------|------------------------------------------|
| `drive:drive.search:readonly`  | Search the user's space                  |
| `drive:drive.metadata:readonly`| Read file metadata                        |
| `drive:file:readonly`          | Download files                           |
| `drive:drive:readonly`         | List user's space root                   |
| `docs:document.content:read`   | Read legacy doc content                  |
| `docs:document.media:download` | Download embedded media                  |
| `docx:document:readonly`       | Read new docx                            |
| `wiki:wiki:readonly`           | Read wiki nodes                          |
| `search:docs:read`             | Cross-space search                       |
| `offline_access`               | (Required) — enables `refresh_token`     |

### How to apply (per scope)

For each scope, click **申请** in the scope's row. A dialog opens asking for
the **申请范围**:

- ✅ **选 "全部用户"** (or "用户身份可用" — the exact label varies by version)
- ❌ **不要选** "仅本应用可见" / "仅租户可用" — those restrict to app identity
  and break the `user_access_token` flow

If you don't see this radio, the scope is already auto-approved for your
account — just apply and move on.

> ⚠️ **`drive:drive:readonly` is not redundant with `drive:drive.search:readonly`.**
> Without it, `GET /drive/v1/files` returns `99991679`
> ("drive:drive, drive:drive:readonly, space:document:retrieve required").

After applying for all 10, **publish a new version** (应用发布 → 创建版本) so
the new scopes take effect for end users. Some scopes can take 1–5 minutes
to propagate after publishing.

---

## 4. Configure the redirect URL

The redirect URL is the address Feishu will send the user's browser to
**after** they approve — the browser will land on `<your URL>/callback?code=…`.
This step has a few gotchas worth being explicit about.

### 4.1 Get the current public URL

```bash
tunnel-url      # prints e.g. https://land-rush-readings-plaza.trycloudflare.com
```

> ⚠️ Cloudflare **quick** tunnels change hostname on every restart. Either
> re-paste after a restart, or switch to a
> [Cloudflare Named Tunnel](https://developers.cloudflare.com/cloudflare-one/connections/connect-networks/)
> for a stable hostname.

### 4.2 Paste the **full URL including the `/callback` path**

In the Feishu console:

- 应用详情 → **开发配置** → **安全设置** → **重定向 URL** → **添加**
- Paste the **full** URL, including the path. For example:
  ```
  https://land-rush-readings-plaza.trycloudflare.com/callback
  ```
- Click **保存** (not just enter — Feishu's UI is easy to miss the save button).

> 🪤 **The path is part of the match.** Feishu compares the configured URL
> **as a whole string** to the `redirect_uri` you pass at auth time.
> If you only paste `https://land-rush-readings-plaza.trycloudflare.com`,
> the auth request will be rejected with `20023 redirect_uri 非法`.
> Make sure `/callback` is on the end.

> You can add **multiple** redirect URLs (e.g. one per environment). Every
> URL you might pass as `redirect_uri` must be in this list.

### 4.3 Verify the configuration is reachable

After saving, test that the URL is publicly reachable **and** that the
tunnel is forwarding traffic to your local server:

```bash
URL=$(tunnel-url)/callback
echo "Testing $URL …"
# Expect HTTP 400 (or 404 if you've not started the oauth-server yet) —
# NOT 404 from Cloudflare, NOT connection refused.
curl -sS -o /dev/null -w "HTTP %{http_code}\n" --max-time 10 "$URL"
```

If you get `HTTP 400` — the tunnel is up AND your `oauth-server.service`
is running. The 400 is the server correctly saying "you called `/callback`
but didn't give me a `code`". This is the **expected** result.

If you get `HTTP 502` — the tunnel is up but `oauth-server.service` is not
running. Start it: `./scripts/start-server.sh`.

If you get `HTTP 404` from Cloudflare — the tunnel isn't up. Start it:
`./scripts/start-tunnel.sh`.

### 4.4 When the tunnel hostname changes

The quick-tunnel hostname changes on every `quick-tunnel.service` restart.
Two options:

- **Easy**: just re-paste the new URL into the Feishu console and save
  (old entries can stay; they just won't be matched).
- **Stable**: switch to a [Cloudflare Named Tunnel]
  (https://developers.cloudflare.com/cloudflare-one/connections/connect-networks/)
  on a domain you own. The hostname is then fixed.

---

## 5. Application availability

- 应用发布 → **可用范围** → make sure your Feishu account is in scope
  (otherwise the user gets `20010` "no app permission" at consent time).

If this is a brand-new 自建应用, the default availability is "仅自己可见",
which is fine for testing — you don't need to add anyone else.

---

## 6. Test the setup

From the project root, with `.env` filled in and both systemd units running:

```bash
tunnel-url                                  # confirm public URL
feishu-auth-url "$(tunnel-url)/callback"    # print the auth URL
# open the printed URL in a browser, approve, watch the callback land
feishu-verify                               # exchange code → token, probe scopes
```

A clean run looks like:

```
Step 1: code → user_access_token       ✅
Step 2: 搜索端点探活                  ✅  drive:drive:readonly
Step 3: refresh_token → 新 access_token ✅  offline_access
```

---

## Symptom → Fix

| Error code | Symptom (Feishu message)                                    | Root cause                                  | Fix |
|-----------|--------------------------------------------------------------|---------------------------------------------|-----|
| `20023`   | redirect_uri 不匹配 / 非法                                    | (a) URL not in 安全设置, or (b) hostname changed after a tunnel restart | Re-paste the current `tunnel-url` output into 安全设置 |
| `20027`   | scope 未申请                                                 | A scope in the URL was not applied for / not published | Check 权限管理 — every scope in the URL must be in the list AND have a published version |
| `20003`   | code 已被使用                                                | `code` is single-use; you re-ran the verify step after the first try | Re-open the auth URL to get a fresh `code` |
| `20004`   | code 已过期                                                  | More than 5 minutes passed between consent and `feishu-verify` | Same — re-open the auth URL |
| `20010`   | 用户无应用权限                                               | Your Feishu account is not in the app's 可用范围 | 应用发布 → 可用范围 → add your account |
| `99991679`| required one of these privileges: `[drive:drive, drive:drive:readonly, …]` | `drive:drive:readonly` not applied for | Apply for it in 权限管理 (see [step 3](#3-apply-for-9-read-scopes--offline_access)) |
| `99992402`| lang is required                                             | The `/application/v6/applications/{app_id}` endpoint requires `?lang=zh_cn` | Add the query param |
| `131002`  | param err                                                    | A wiki node endpoint was called with a non-wiki token | Pass a wiki-space token, not a folder/docx token |
| `1770002` | not found                                                    | Endpoint called on a token of the wrong type (e.g. `/docx/v1/documents/<folder-token>`) | Use the right endpoint for the token's type (folder, docx, bitable, wiki) |

If your error isn't in the table, the full body is JSON in
`feishu-user-tokens.json` under `_error` after a failed call — paste it
back to the model for a closer look.
