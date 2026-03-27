# briefing.py -- Data briefing endpoint.
# Depends on: config.py
# Depended on by: main.py (router registration)
from __future__ import annotations

import json
import queue
import threading
from datetime import datetime

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse

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


@router.get("/briefing/refresh")
def refresh_briefing_sse():
    """Run the data agent with Server-Sent Events progress streaming.

    Returns an SSE stream with progress events as the data agent works through
    FRED series, Yahoo tickers, and derived metrics. The final event contains
    the result summary.

    Use GET (not POST) because SSE via EventSource requires GET.
    """
    import logging
    from backend.engine.data_agent import build_briefing

    logger = logging.getLogger(__name__)

    # Thread-safe queue for progress events
    progress_q: queue.Queue = queue.Queue()

    def on_progress(stage: str, detail: str):
        progress_q.put({"stage": stage, "detail": detail})

    def run_agent():
        """Run the data agent in a background thread, pushing progress events."""
        try:
            packet = build_briefing(use_cache=False, on_progress=on_progress)

            # Save to both data/ and mock_data/
            packet_dict = packet.model_dump()
            for out_dir in [DATA_DIR, MOCK_DATA_DIR]:
                out_dir.mkdir(parents=True, exist_ok=True)
                out_path = out_dir / "briefing_packet.json"
                out_path.write_text(
                    json.dumps(packet_dict, indent=2, default=str),
                    encoding="utf-8",
                )

            progress_q.put({
                "stage": "complete",
                "detail": f"Done. {len(packet_dict.get('markets', {}))} tickers fetched.",
                "timestamp": packet_dict.get("timestamp", ""),
                "markets_count": len(packet_dict.get("markets", {})),
            })
        except Exception as e:
            logger.exception("Data agent refresh failed")
            progress_q.put({"stage": "error", "detail": str(e)})
        finally:
            progress_q.put(None)  # Sentinel: stream is done

    def event_stream():
        """Generator that yields SSE-formatted events from the progress queue."""
        thread = threading.Thread(target=run_agent, daemon=True)
        thread.start()

        while True:
            try:
                msg = progress_q.get(timeout=120)
            except queue.Empty:
                yield "data: {\"stage\": \"error\", \"detail\": \"Timeout waiting for data agent\"}\n\n"
                break

            if msg is None:
                break

            yield f"data: {json.dumps(msg)}\n\n"

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
