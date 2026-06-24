"""Configuration loader. All secrets come from the environment — never hard-code."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


def _load_dotenv(path: Path) -> None:
    """Tiny .env loader — no external dependency, no override of existing env."""
    if not path.exists():
        return
    for line in path.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        k = k.strip()
        v = v.strip().strip('"').strip("'")
        os.environ.setdefault(k, v)


# Load .env from the current working directory if present
_load_dotenv(Path.cwd() / ".env")


@dataclass(frozen=True)
class FeishuConfig:
    app_id: str
    app_secret: str
    token_file: Path
    code_file: Path

    @property
    def has_secret(self) -> bool:
        return bool(self.app_id) and bool(self.app_secret)


def load_config() -> FeishuConfig:
    """Read APP_ID and APP_SECRET from the environment. Raise clearly if missing."""
    app_id = os.environ.get("FEISHU_APP_ID", "").strip()
    app_secret = os.environ.get("FEISHU_APP_SECRET", "").strip()

    if not app_id or not app_secret:
        raise SystemExit(
            "❌ FEISHU_APP_ID / FEISHU_APP_SECRET not set.\n"
            "   Copy .env.example to .env and fill them in, or export them in your shell."
        )

    return FeishuConfig(
        app_id=app_id,
        app_secret=app_secret,
        token_file=Path(
            os.environ.get("FEISHU_TOKEN_FILE", Path.cwd() / "feishu-user-tokens.json")
        ),
        code_file=Path(
            os.environ.get("FEISHU_CODE_FILE", Path.cwd() / "code.txt")
        ),
    )
