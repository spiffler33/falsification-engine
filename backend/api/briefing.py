# briefing.py -- Data briefing endpoint.
# Depends on: config.py
# Depended on by: main.py (router registration)
from __future__ import annotations

import json
from datetime import datetime

from fastapi import APIRouter, HTTPException

from backend.config import DATA_DIR, MOCK_DATA_DIR

router = APIRouter(tags=["briefing"])


@router.get("/briefing/latest")
def get_latest_briefing():
    """Serve the latest data briefing packet with staleness metadata."""
    # Try real briefing first, fall back to mock
    for path in [DATA_DIR / "briefing_packet.json", MOCK_DATA_DIR / "briefing_packet.json"]:
        if path.exists():
            data = json.loads(path.read_text(encoding="utf-8"))

            # Compute staleness
            timestamp = data.get("timestamp", "")
            staleness_hours = 0.0
            is_mock = "mock_data" in str(path)

            if timestamp:
                try:
                    ts = datetime.fromisoformat(timestamp)
                    staleness_hours = (datetime.now() - ts).total_seconds() / 3600
                except (ValueError, TypeError):
                    staleness_hours = -1  # unknown

            return {
                "data": data,
                "staleness_hours": round(staleness_hours, 1),
                "is_mock": is_mock,
                "source_path": str(path),
            }

    raise HTTPException(status_code=404, detail="No briefing packet found. Run scripts/run_data.py first.")
