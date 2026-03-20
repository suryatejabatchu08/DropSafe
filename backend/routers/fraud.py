from fastapi import APIRouter
from pydantic import BaseModel, Field

router = APIRouter(prefix="/fraud", tags=["fraud"])


class FraudScoreRequest(BaseModel):
    gps_match: bool
    order_volume_collapsed: bool
    cell_tower_match: bool
    shift_active: bool


class FraudScoreResponse(BaseModel):
    fraud_score: float = Field(..., ge=0.0, le=1.0)


@router.post("/score", response_model=FraudScoreResponse)
async def fraud_score(payload: FraudScoreRequest):
    # Simple weighted "probability of fraud" for Phase 1 demo purposes.
    # Suspicious conditions push the score toward 1.0.
    weights = {
        "gps_mismatch": 0.35,
        "order_volume_not_collapsed": 0.25,
        "cell_tower_mismatch": 0.25,
        "shift_inactive": 0.15,
    }

    suspicious_sum = 0.0
    if not payload.gps_match:
        suspicious_sum += weights["gps_mismatch"]
    if not payload.order_volume_collapsed:
        suspicious_sum += weights["order_volume_not_collapsed"]
    if not payload.cell_tower_match:
        suspicious_sum += weights["cell_tower_mismatch"]
    if not payload.shift_active:
        suspicious_sum += weights["shift_inactive"]

    # weights intentionally sum to 1.0
    fraud_score_value = max(0.0, min(1.0, suspicious_sum))
    return FraudScoreResponse(fraud_score=round(fraud_score_value, 3))

