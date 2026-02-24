from __future__ import annotations

from datetime import UTC, datetime


def now_iso() -> str:
    return datetime.now(tz=UTC).isoformat().replace("+00:00", "Z")
