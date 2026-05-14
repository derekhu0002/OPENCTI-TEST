from __future__ import annotations

import json
import os
import time
from datetime import UTC, datetime
from pathlib import Path

RUNTIME_DIR = Path(__file__).resolve().parent / "runtime"
FRESHNESS_PATH = RUNTIME_DIR / "freshness.json"
ANCHOR_PATH = RUNTIME_DIR / "test_bootstrap_anchor.json"


def _current_timestamp() -> str:
    return datetime.now(UTC).isoformat().replace("+00:00", "Z")


def _runtime_state() -> dict[str, object]:
    bootstrap_start_at = os.getenv("BOOTSTRAP_START_AT", "").strip()
    if not bootstrap_start_at and ANCHOR_PATH.is_file():
        payload = json.loads(ANCHOR_PATH.read_text(encoding="utf-8"))
        bootstrap_start_at = str(payload.get("bootstrap_start_at", "")).strip()

    return {
        "backend": "neo4j-replica",
        "freshness_ts": _current_timestamp(),
        "staleness_seconds": 0,
        "sync_status": "starting",
        "opencti_url": os.getenv("OPENCTI_URL", "").strip(),
        "stream_id": os.getenv("STREAM_ID", "").strip(),
        "bootstrap_start_at": bootstrap_start_at,
        "bootstrap_lookback_days": os.getenv("MIRROR_BOOTSTRAP_LOOKBACK_DAYS", "365").strip(),
    }


def _write_freshness() -> None:
    RUNTIME_DIR.mkdir(parents=True, exist_ok=True)
    FRESHNESS_PATH.write_text(json.dumps(_runtime_state(), indent=2), encoding="utf-8")


def main() -> None:
    poll_interval_seconds = int(os.getenv("MIRROR_POLL_INTERVAL_SECONDS", "15"))
    while True:
        _write_freshness()
        time.sleep(max(poll_interval_seconds, 1))


if __name__ == "__main__":
    main()
