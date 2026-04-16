"""
DropSafe ML Router
Endpoints for Isolation Forest model management and testing.
"""

import time
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from datetime import datetime, timedelta
from typing import Optional, Any
import os
import json
import pytz

router = APIRouter(prefix="/ml", tags=["ml"])

IST = pytz.timezone("Asia/Kolkata")

MODELS_DIR = os.path.join(os.path.dirname(__file__), "..", "models")
METADATA_PATH = os.path.join(MODELS_DIR, "model_metadata.json")


def _load_metadata() -> dict:
    """Load model metadata JSON, or return empty dict if missing."""
    try:
        if os.path.exists(METADATA_PATH):
            with open(METADATA_PATH) as f:
                return json.load(f)
    except Exception:
        pass
    return {}


# ─────────────────────────────────────────────────────────────────────────────
# POST /ml/train
# ─────────────────────────────────────────────────────────────────────────────

@router.post("/train")
async def trigger_retrain():
    """
    Trigger Isolation Forest retraining.

    Uses all real claims from Supabase + synthetic data if < 50 real claims.
    After training, reloads the model into the scorer cache.

    Returns:
        { samples_used, training_time_sec, model_version, contamination, bias_metrics }
    """
    try:
        from services.isolation_forest_trainer import IsolationForestTrainer
        from services.isolation_forest_scorer import IsolationForestScorer

        print("[ML Router] Retraining triggered via API...")
        result = await IsolationForestTrainer.train()

        # Reload scorer cache with new model
        IsolationForestScorer.reload()
        print("[ML Router] Model reloaded into scorer cache ✅")

        return {
            "status": "success",
            "message": "Isolation Forest retrained and reloaded",
            **result,
        }

    except Exception as e:
        print(f"[ML Router] Training failed: {e}")
        raise HTTPException(status_code=500, detail=f"Training failed: {str(e)}")


# ─────────────────────────────────────────────────────────────────────────────
# GET /ml/model/status
# ─────────────────────────────────────────────────────────────────────────────

@router.get("/model/status")
async def get_model_status():
    """
    Get model metadata and recent fraud scoring statistics.

    Returns:
        {
            trained_at, samples_used, contamination_rate, model_version,
            scaler, features, bias_metrics,
            avg_fraud_score_last_7d, claims_scored_last_7d,
            model_loaded
        }
    """
    try:
        from services.isolation_forest_scorer import IsolationForestScorer
        from database import get_supabase

        metadata = _load_metadata()

        # Recent fraud scoring stats from claims
        supabase = get_supabase()
        seven_days_ago = (datetime.now(IST) - timedelta(days=7)).replace(
            tzinfo=None
        ).isoformat()

        claims_resp = (
            supabase.table("claims")
            .select("fraud_score, fraud_flags")
            .gte("created_at", seven_days_ago)
            .execute()
        )

        claims = claims_resp.data or []
        scores = [c.get("fraud_score", 0) for c in claims if c.get("fraud_score")]
        avg_score = round(sum(scores) / len(scores), 3) if scores else None

        # Count how many claims had Layer 2 applied
        l2_applied = sum(
            1 for c in claims
            if isinstance(c.get("fraud_flags"), dict)
            and c["fraud_flags"].get("layer2_isolation_forest", {}).get("score") is not None
        )

        return {
            "model_loaded": IsolationForestScorer.is_loaded(),
            "trained_at": metadata.get("trained_at"),
            "samples_used": metadata.get("samples_used"),
            "contamination_rate": metadata.get("contamination"),
            "model_version": metadata.get("model_version"),
            "scaler": metadata.get("scaler"),
            "feature_names": metadata.get("feature_names"),
            "training_time_sec": metadata.get("training_time_sec"),
            "bias_metrics": metadata.get("bias_metrics"),
            "avg_fraud_score_last_7d": avg_score,
            "claims_scored_last_7d": len(claims),
            "layer2_applied_last_7d": l2_applied,
        }

    except Exception as e:
        print(f"[ML Router] Status check failed: {e}")
        raise HTTPException(status_code=500, detail=f"Status check failed: {str(e)}")


# ─────────────────────────────────────────────────────────────────────────────
# POST /ml/score/test
# ─────────────────────────────────────────────────────────────────────────────

class TestScoreRequest(BaseModel):
    # Layer 1 features (will run actual rule engine simulation)
    fraud_score_layer1: float = 0.25         # Simulated Layer 1 output
    payout_amount: float = 240.0             # ₹
    disrupted_hours: float = 3.0
    hour_of_day: int = 14                    # 2 PM
    day_of_week: int = 2                     # Wednesday
    worker_claim_count_30d: int = 3
    zone_claim_count_hour: int = 4
    worker_days_registered: int = 120
    zone_risk_multiplier: float = 1.2
    trigger_severity: float = 0.65
    is_weekend: int = 0
    is_peak_hours: int = 1
    # Scenario label (for demo clarity)
    scenario: str = "normal"  # "normal" | "fraud"


@router.post("/score/test")
async def test_score(req: TestScoreRequest):
    """
    Test endpoint — demonstrates Layer 1 + Layer 2 scoring separately.

    Accepts mock claim features and shows how both layers combine.
    Designed for judges and demo purposes.

    Returns:
        {
            layer1_score, layer2_score, combined_score,
            combined_formula, verdict, explanation
        }
    """
    try:
        from services.isolation_forest_scorer import IsolationForestScorer

        layer1_score = req.fraud_score_layer1

        # Build feature vector and score with Layer 2
        features = [
            req.fraud_score_layer1,
            req.payout_amount,
            req.disrupted_hours,
            float(req.hour_of_day),
            float(req.day_of_week),
            float(req.worker_claim_count_30d),
            float(req.zone_claim_count_hour),
            float(req.worker_days_registered),
            req.zone_risk_multiplier,
            req.trigger_severity,
            float(req.is_weekend),
            float(req.is_peak_hours),
        ]

        layer2_score = layer1_score  # Default if model not loaded
        model_used = "layer1_fallback"

        if IsolationForestScorer.is_loaded():
            import asyncio
            import numpy as np

            loop = asyncio.get_event_loop()
            layer2_score = await asyncio.wait_for(
                loop.run_in_executor(
                    None, IsolationForestScorer._score_sync, features
                ),
                timeout=2.0,
            )
            model_used = "IsolationForest_v1"

        combined = round((layer1_score * 0.60) + (layer2_score * 0.40), 3)

        if combined < 0.40:
            verdict = "AUTO_APPROVE ✅"
        elif combined < 0.80:
            verdict = "SEND TO REVIEW 🔍"
        else:
            verdict = "AUTO_REJECT ❌"

        return {
            "scenario": req.scenario,
            "layer1_score": round(layer1_score, 3),
            "layer1_description": "Rule-based MSAS (GPS, timing, frequency, duplicate, activity, new worker, cluster)",
            "layer2_score": round(layer2_score, 3),
            "layer2_description": f"Isolation Forest anomaly detection ({model_used})",
            "combined_score": combined,
            "combined_formula": f"({layer1_score:.3f} × 0.60) + ({layer2_score:.3f} × 0.40) = {combined:.3f}",
            "verdict": verdict,
            "thresholds": {
                "auto_approve": "< 0.40",
                "review": "0.40 – 0.80",
                "auto_reject": "> 0.80",
            },
            "model_used": model_used,
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Test scoring failed: {str(e)}")
