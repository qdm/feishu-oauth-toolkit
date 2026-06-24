# 飞书 (Feishu) backend setup checklist

These are the manual steps you need to complete in the Feishu developer console
**before** `feishu-verify` can succeed. Captured from a real test on
2026-06-24 against a 自建应用 named `cloud`.

## 1. App credentials

- 飞书开放平台 → 你的应用 → 凭证与基础信息
- Copy `App ID` (looks like `cli_xxxxxxxxxxxx`) and `App Secret` into `.env`:
  ```
  FEISHU_APP_ID=cli_xxxxxxxxxxxx
  FEISHU_APP_SECRET=your-secret
  ```

## 2. Enable the "网页应用" capability

- 应用详情 → 应用能力 → 添加能力 → 选 **网页应用**
- Required so the OAuth redirect-URL field appears in 安全设置
- (For a pure headless CLI, you do **not** need to fill in the desktop/mobile
  homepage URL — those are only relevant for users clicking into the app from
  the Feishu client.)

## 3. Apply for 9 read scopes + offline_access

In 权限管理, apply for these (all need **用户身份可用** ticked):

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

> ⚠️ `drive:drive:readonly` is **not** redundant with `drive:drive.search:readonly`.
> Without it, `GET /drive/v1/files` returns 99991679 ("drive:drive, drive:drive:readonly, space:document:retrieve required").

After applying, **publish a new version** so the new scopes take effect for end users.

## 4. Configure the redirect URL

- 应用详情 → 开发配置 → 安全设置 → 重定向 URL → 添加
- Paste the URL printed by `./scripts/tunnel-url.sh` (looks like
  `https://xyz.trycloudflare.com/callback`)
- **Important**: if the cloudflared quick tunnel restarts, the URL changes.
  Either re-paste the new URL, or switch to a [Cloudflare Named Tunnel]
  (https://developers.cloudflare.com/cloudflare-one/connections/connect-networks/)
  for a stable hostname.

## 5. Application availability

- 应用发布 → 可用范围 → make sure your Feishu account is in scope
  (otherwise the user gets 20010 "no app permission" at consent time)
