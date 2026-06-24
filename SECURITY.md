# Security model

This project handles two kinds of secret: **App credentials** (issued by Feishu)
and **OAuth tokens** (issued by Feishu at runtime in exchange for a one-time
`code`).

## App credentials

The Feishu `App ID` and `App Secret` are configured via the
`FEISHU_APP_ID` and `FEISHU_APP_SECRET` environment variables. They are
**never** hard-coded anywhere in the source tree.

The `.env.example` file is a template only; you copy it to `.env` and fill
in your own values. `.env` is git-ignored, so your real credentials will
never be committed even by accident.

If you suspect your `App Secret` has leaked, rotate it from the Feishu
developer console immediately and re-issue tokens.

## OAuth tokens

After the user grants consent, Feishu returns an `access_token` and (if
`offline_access` was granted) a `refresh_token`. The toolkit writes these to
`feishu-user-tokens.json` in the working directory, with file mode `0600`.
That path is also git-ignored.

- `access_token` — 2 hour TTL
- `refresh_token` — 7 day TTL, **single use** (each refresh issues a new one)
- The file includes `_issued_at`, `_expires_at`, and `_refresh_expires_at`
  for downstream callers that want to schedule proactive refresh.

## What ships in this repo

```
16 files / 100 KB / 451 LoC of Python
```

A `grep -r "FEISHU_APP_SECRET" .` against the source tree should return
**zero hits**. Run it yourself to verify after every change.

## Tunnel exposure

The `cloudflared quick tunnel` exposes your `127.0.0.1:18080` to the
public internet under a Cloudflare-owned hostname. The hostname is
ephemeral (changes on every restart of `quick-tunnel.service`) and has
**no uptime guarantee** — see [Cloudflare's terms](https://www.cloudflare.com/website-terms/).

For a long-running deployment, switch to a
[Cloudflare Named Tunnel](https://developers.cloudflare.com/cloudflare-one/connections/connect-networks/)
with your own domain.
