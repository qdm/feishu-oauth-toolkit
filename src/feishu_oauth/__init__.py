"""Feishu OAuth toolkit — headless Authorization Code flow helper.

Public API:
    - feishu_oauth.config:   load APP_ID / APP_SECRET from environment
    - feishu_oauth.auth:     build auth URL, exchange code, refresh token
    - feishu_oauth.server:   run a localhost HTTP server that captures the callback
    - feishu_oauth.verify:   end-to-end verification CLI
"""

__version__ = "0.1.0"
