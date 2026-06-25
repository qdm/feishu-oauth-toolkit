"""Tiny HTTP server that captures the OAuth callback and writes the code to disk."""

from __future__ import annotations

import http.server
import json
import sys
import urllib.parse
from pathlib import Path

from .config import load_config

DEFAULT_PORT = 18080

HTML_SUCCESS = """<!doctype html>
<html><head><meta charset="utf-8"><title>授权成功</title>
<style>body{font-family:-apple-system,sans-serif;max-width:560px;margin:60px auto;padding:0 24px;color:#333}
.box{background:#e8f5e9;border-left:4px solid #4caf50;padding:20px 24px;border-radius:4px}
h1{margin-top:0;font-size:20px}
code{background:#f5f5f5;padding:2px 6px;border-radius:3px;font-size:13px;word-break:break-all}
</style></head>
<body>
<div class="box">
<h1>✅ 授权 code 已收到</h1>
<p>你可以关闭这个页面,回到终端继续验证。</p>
<p style="font-size:13px;color:#666">code 已保存到: <code>__CODE_FILE__</code></p>
</div>
</body></html>
"""

HTML_ERROR_TPL = """<!doctype html>
<html><head><meta charset="utf-8"><title>授权失败</title>
<style>body{font-family:-apple-system,sans-serif;max-width:560px;margin:60px auto;padding:0 24px;color:#333}
.box{background:#ffebee;border-left:4px solid #f44336;padding:20px 24px;border-radius:4px}
h1{margin-top:0;font-size:20px}
</style></head>
<body>
<div class="box">
<h1>❌ 授权失败</h1>
<p>__MSG__</p>
</div>
</body></html>
"""


def _html_escape(s: str) -> str:
    """HTML escape (避免 msg 里带 < > & 破坏页面)."""
    return (
        s.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
    )


class Handler(http.server.BaseHTTPRequestHandler):
    code_file: Path  # set in main()

    def log_message(self, fmt: str, *args: object) -> None:  # noqa: D401
        sys.stderr.write(f"[{self.log_date_time_string()}] {fmt % args}\n")

    def do_GET(self) -> None:
        parsed = urllib.parse.urlparse(self.path)
        params = urllib.parse.parse_qs(parsed.query)

        if parsed.path == "/health":
            self.send_response(200)
            self.send_header("Content-Type", "text/plain")
            self.end_headers()
            self.wfile.write(b"ok")
            return

        if parsed.path != "/callback":
            self.send_response(404)
            self.send_header("Content-Type", "text/plain")
            self.end_headers()
            self.wfile.write(b"not found")
            return

        code = params.get("code", [None])[0]
        state = params.get("state", [None])[0]
        error = params.get("error", [None])[0]
        error_desc = params.get("error_description", [None])[0]

        if error or not code:
            msg = f"error={error}, description={error_desc}" if error else "callback 缺少 code 参数"
            print(f"[ERROR] {msg}", flush=True)
            # 用 str.replace 占位符,避开 HTML_ERROR_TPL 里的 CSS {font-family...} 被 .format() 当占位符
            body = HTML_ERROR_TPL.replace("__MSG__", _html_escape(msg))
            self._html(400, body)
            return

        self.code_file.write_text(
            json.dumps(
                {"code": code, "state": state, "received_at": self.log_date_time_string()},
                ensure_ascii=False,
                indent=2,
            )
        )
        self.code_file.chmod(0o600)
        print(f"[OK] code 已收到,长度 {len(code)},已写入 {self.code_file}", flush=True)

        # 用 str.replace 占位符,避开 HTML_SUCCESS 里 CSS {font-family...} 被 .format() 当占位符
        body = HTML_SUCCESS.replace("__CODE_FILE__", _html_escape(str(self.code_file)))
        self._html(200, body)

    def _html(self, status: int, body: str) -> None:
        self.send_response(status)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.end_headers()
        self.wfile.write(body.encode("utf-8"))


def cli_main() -> None:
    cfg = load_config()
    port = DEFAULT_PORT
    if len(sys.argv) > 1:
        port = int(sys.argv[1])

    Handler.code_file = cfg.code_file
    server = http.server.HTTPServer(("127.0.0.1", port), Handler)
    print(f"[START] OAuth callback server listening on http://127.0.0.1:{port}/callback", flush=True)
    print(f"[INFO]  code 落地文件: {cfg.code_file}", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        server.server_close()
        print("\n[STOP] server stopped", flush=True)


if __name__ == "__main__":
    cli_main()
