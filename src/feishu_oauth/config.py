"""Configuration loader. All secrets come from the environment — never hard-code."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


def _load_dotenv(path: Path) -> None:
    """Tiny .env loader — if .env exists, .env wins over inherited env vars.

    强制覆盖(而非 setdefault):在 OAuth 这种 secret-敏感场景, .env 应该是 single source of truth.
    否则从父进程继承的 FEISHU_APP_ID 会悄悄覆盖掉 .env 里的值(像我们之前踩的:
    .env 写自己的 app_id, process env 有 OpenClaw 默认的另一个, 拿到的是错的).
    """
    if not path.exists():
        return
    for line in path.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        k = k.strip()
        v = v.strip().strip('"').strip("'")
        os.environ[k] = v  # 强制 .env 覆盖


# Load .env from (in order):
#   1. current working directory (developer override)
#   2. the package's install location (production / systemd)
# First one that exists wins.
def _find_dotenv() -> Path | None:
    """Find the .env file in (in order):
      1. current working directory (developer override)
      2. the project root (relative to this package, two levels up:
         src/feishu_oauth/config.py -> src/feishu_oauth/ -> src/ -> repo root)
      3. the parent of this package (legacy pip install layout)

    First one that exists wins.
    """
    candidates: list[Path] = [Path.cwd() / ".env"]
    pkg_dir = Path(__file__).resolve().parent  # src/feishu_oauth
    # repo root (when installed editable from src/)
    candidates.append(pkg_dir.parent.parent / ".env")
    # one level up (legacy install layout)
    candidates.append(pkg_dir.parent / ".env")
    for p in candidates:
        if p.exists():
            return p
    return None


dotenv_path = _find_dotenv()
if dotenv_path is not None:
    _load_dotenv(dotenv_path)


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
