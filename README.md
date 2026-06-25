# Feishu OAuth Toolkit

End-to-end CLI toolkit for running the **飞书 (Feishu/Lark) OAuth 2.0 Authorization Code flow** end-to-end on a headless server — including:

- A minimal local HTTP server to receive the `code` callback
- A `cloudflared` quick tunnel so the callback can be reached over a public HTTPS URL (no domain or account required)
- A `systemd --user` service pair that keeps both running in the background
- Verification scripts that exchange `code → user_access_token`, then probe each requested scope against the Feishu Open API
- Token refresh (`offline_access`) round-trip verification

Tested end-to-end against a custom app (自建应用) with the nine read scopes
listed in [docs/feishu-backend-setup.md](docs/feishu-backend-setup.md). No
credentials ship in this repo — see [SECURITY.md](SECURITY.md) for the
security model.

---

## What's in the box

```
feishu-oauth-toolkit/
├── src/feishu_oauth/
│   ├── config.py            # reads APP_ID / APP_SECRET from env (no hard-coded secrets)
│   ├── auth.py              # build_auth_url, exchange_code, refresh
│   ├── server.py            # localhost HTTP server that captures the OAuth code
│   └── verify.py            # end-to-end verification (code → token → scope probes)
├── scripts/
│   ├── start-tunnel.sh      # installs cloudflared + writes systemd unit
│   ├── start-server.sh      # writes oauth-server systemd unit
│   ├── tunnel-url.sh        # prints the current public trycloudflare URL
│   └── systemd/             # checked-in unit files
│       ├── quick-tunnel.service
│       └── oauth-server.service
├── docs/
│   └── feishu-backend-setup.md   # how to enable Web App + apply the 9 scopes
├── .env.example             # template — copy to .env and fill in your own values
├── .gitignore               # .env, *.json tokens, __pycache__, etc.
├── pyproject.toml           # exposes 3 console scripts (see below)
├── LICENSE
├── README.md
└── SECURITY.md
```

## Prerequisites

- Linux with `systemd` (verified on Ubuntu 22.04 / 24.04)
- Python ≥ 3.10
- A Feishu 自建应用 (custom app) — see [docs/feishu-backend-setup.md](docs/feishu-backend-setup.md)

## Quick start

```bash
# 1. Install
git clone https://github.com/qdm/feishu-oauth-toolkit.git
cd feishu-oauth-toolkit
python3 -m venv .venv && source .venv/bin/activate
pip install -e .                 # installs the 3 console scripts below

# 2. Configure secrets (NEVER commit this file)
cp .env.example .env
$EDITOR .env                     # fill FEISHU_APP_ID and FEISHU_APP_SECRET

# 3. Install the tunnel-url helper (root-free, ~/.local/bin)
mkdir -p ~/.local/bin
cp scripts/tunnel-url.sh ~/.local/bin/tunnel-url
# add ~/.local/bin to PATH if not already
export PATH="$HOME/.local/bin:$PATH"

# 4. Install cloudflared and start the tunnel + callback server
./scripts/start-tunnel.sh        # systemd --user quick-tunnel → *.trycloudflare.com
./scripts/start-server.sh        # systemd --user oauth-server → 127.0.0.1:18080

# 5. Get the public URL and paste it into the Feishu backend
tunnel-url                       # prints e.g. https://xyz.trycloudflare.com
# (Cloudflare quick tunnels change hostname on every restart — re-paste if it does)

# 6. Generate the authorization URL
feishu-auth-url "https://xyz.trycloudflare.com/callback"
# open the printed URL in a browser, approve, watch the callback land

# 7. Run the end-to-end verification
feishu-verify                    # exchanges code → token, probes scopes, refreshes
```

### The 3 console scripts

After `pip install -e .` you get:

| Script              | Purpose                                              |
|---------------------|------------------------------------------------------|
| `feishu-auth-url`   | Print the user-facing authorization URL for a given `redirect_uri` |
| `feishu-verify`     | Read the captured `code`, exchange for tokens, probe scopes, refresh |
| `feishu-server`     | Run the localhost callback server (also available as a systemd --user unit) |

## Security model

- **No secrets in source.** `config.py` reads from environment variables. `.env` is git-ignored.
- **Public tunnel has no uptime guarantee.** Cloudflare quick tunnels are free and ephemeral; the hostname changes on every restart. If you need a stable URL, use a [Cloudflare Named Tunnel](https://developers.cloudflare.com/cloudflare-one/connections/connect-networks/) with your own domain.
- **Tokens never leave disk unencrypted.** `feishu-user-tokens.json` is written to the working directory with `chmod 600`. Add it to your own backup strategy.

See [SECURITY.md](SECURITY.md) for the full secret-handling model.

## Scope matrix verified

| Scope                          | Verified endpoint                          | Status |
|--------------------------------|--------------------------------------------|--------|
| `drive:drive.search:readonly`  | `GET /drive/v1/files`                      | ✅     |
| `drive:drive.metadata:readonly`| `GET /drive/v1/files/:token`               | ✅     |
| `drive:file:readonly`          | `GET /drive/v1/files/:token/download`      | ✅     |
| `drive:drive:readonly`         | `GET /drive/v1/files?folder=root`          | ✅     |
| `docs:document.content:read`   | `GET /docs/v1/content/:token`              | ✅     |
| `docs:document.media:download` | `GET /drive/v1/medias/:token/download`     | ✅     |
| `docx:document:readonly`       | `GET /docx/v1/documents/:token`            | ✅     |
| `wiki:wiki:readonly`           | `GET /wiki/v2/spaces/get_node?token=…`     | ✅     |
| `search:docs:read`             | (search v2 API)                            | ✅     |
| `offline_access`               | `POST /authen/v2/oauth/token` (refresh)    | ✅     |

See [docs/feishu-backend-setup.md](docs/feishu-backend-setup.md) for the exact
backend steps required before you can use these scopes, and for the most
common first-time-setup failure (an empty Web App home URL, 主页 URL).

## License

MIT — see [LICENSE](LICENSE).
