from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

router = APIRouter(prefix="/premium", tags=["premium"])


class PremiumCalculateRequest(BaseModel):
    zone_risk: float = Field(..., ge=0.0)
    declared_hours: int = Field(..., ge=0)
    season: str


SEASONAL_INDEX = {
    "normal": 1.0,
    "monsoon": 1.3,
    "aqi_season": 1.25,
}


@router.post("/calculate")
async def calculate_premium(payload: PremiumCalculateRequest):
    seasonal_index = SEASONAL_INDEX.get(payload.season)
    if seasonal_index is None:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid season. Expected one of: {', '.join(SEASONAL_INDEX.keys())}",
        )

    base_rate = 38.0
    hours_ratio = payload.declared_hours / 40.0

    weekly_premium = base_rate * payload.zone_risk * hours_ratio * seasonal_index
    return {"weekly_premium": round(weekly_premium, 2)}

