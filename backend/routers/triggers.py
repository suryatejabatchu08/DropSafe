from datetime import datetime, timezone

from fastapi import APIRouter

router = APIRouter(prefix="/triggers", tags=["triggers"])


@router.get("/mock")
async def mock_triggers():
    # Hardcoded sample "active" events for Phase 1 demo.
    now = datetime.now(timezone.utc).isoformat()
    return [
        {
            "trigger_type": "rain",
            "zone": "Koramangala, Bengaluru",
            "severity": 0.82,
            "timestamp": now,
        },
        {
            "trigger_type": "aqi",
            "zone": "Dwarka, Delhi NCR",
            "severity": 0.91,
            "timestamp": now,
        },
        {
            "trigger_type": "rain",
            "zone": "Andheri West, Mumbai",
            "severity": 0.63,
            "timestamp": now,
        },
    ]

