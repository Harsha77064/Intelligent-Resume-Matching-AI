"""MatchPoint backend.

Settings can be put in backend/.env (one KEY=VALUE per line), e.g.

    SEED_DEMO=0
    SECRET_KEY=change-me-to-a-long-random-string

Real environment variables take priority over the file.
"""
import os
from pathlib import Path

_env = Path(__file__).resolve().parent.parent / ".env"
if _env.exists():
    for _line in _env.read_text(encoding="utf-8").splitlines():
        _line = _line.strip()
        if _line and not _line.startswith("#") and "=" in _line:
            _key, _val = _line.split("=", 1)
            os.environ.setdefault(_key.strip(), _val.strip().strip('"').strip("'"))
