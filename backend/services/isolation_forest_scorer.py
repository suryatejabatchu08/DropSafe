"""
DropSafe — Isolation Forest Scorer (Fraud Detection Layer 2)

Loads the trained model once at startup and caches it in memory.
Scores individual claims asynchronously with a 2-second timeout.
Falls back to Layer 1 score if model is unavailable or too slow.
"""

import os
import asyncio
import numpy as np
import joblib
import pytz
from datetime import datetime

IST = pytz.timezone("Asia/Kolkata")

MODELS_DIR = os.path.join(os.path.dirname(__file__), "..", "models")
MODEL_PATH = os.path.join(MODELS_DIR, "isolation_forest.pkl")
SCALER_PATH = os.path.join(MODELS_DIR, "scaler.pkl")

FEATURE_NAMES = [
    "fraud_score_layer1",
    "payout_amount",
    "disrupted_hours",
    "hour_of_day",
    "day_of_week",
    "worker_claim_count_30d",
    "zone_claim_count_hour",
    "worker_days_registered",
    "zone_risk_multiplier",
    "trigger_severity",
    "is_weekend",
    "is_peak_hours",
]

PEAK_HOURS = {12, 13, 19, 20, 21}


class IsolationForestScorer:
    """
    Singleton-style scorer — model loaded once, reused for every claim.

    Timeout: 2 seconds max. If model is slow or unavailable,
    falls back gracefully to a neutral score (0.3) so claim
    processing is never blocked.
    """

    _model = None
    _scaler = None
    _loaded = False

    # ─────────────────────────────────────────────────────────────────────────
    # Model Loading
    # ─────────────────────────────────────────────────────────────────────────

    @classmethod
    def load_model(cls):
        """Load model and scaler from disk. Called once at startup."""
        try:
            if not os.path.exists(MODEL_PATH):
                print(f"[IFScorer] Model not found at {MODEL_PATH}")
                return False

            cls._model = joblib.load(MODEL_PATH)
            cls._scaler = joblib.load(SCALER_PATH)
            cls._loaded = True
            print("[IFScorer] ✅ Isolation Forest model loaded from disk")
            return True

        except Exception as e:
            print(f"[IFScorer] ❌ Failed to load model: {e}")
            cls._loaded = False
            return False

    @classmethod
    def is_loaded(cls) -> bool:
        return cls._loaded and cls._model is not None and cls._scaler is not None

    @classmethod
    def reload(cls):
        """Force reload from disk (called after retraining)."""
        cls._model = None
        cls._scaler = None
        cls._loaded = False
        return cls.load_model()

    # ─────────────────────────────────────────────────────────────────────────
    # Feature Building
    # ─────────────────────────────────────────────────────────────────────────

    @classmethod
    def _build_feature_vector(
        cls,
        claim: dict,
        worker: dict,
        trigger: dict,
        zone: dict,
        layer1_score: float,
        worker_claim_count_30d: int = 2,
        zone_claim_count_hour: int = 1,
    ) -> list:
        """
        Build the 12-feature vector for a single claim at inference time.

        Args:
            claim:   Claim record (payout_amount, disrupted_hours, created_at)
            worker:  Worker record (created_at, avg_hourly_income)
            trigger: Trigger event (severity)
            zone:    Zone record (risk_multiplier)
            layer1_score: Output of the rule-based engine (fraud_score_layer1)
            worker_claim_count_30d: How many claims this worker filed in 30d
            zone_claim_count_hour:  How many claims in zone in same hour
        """
        # Timestamp features
        try:
            created_at_str = claim.get("created_at", "")
            if created_at_str:
                from datetime import timezone
                dt = datetime.fromisoformat(str(created_at_str).replace("Z", "+00:00"))
                dt_ist = dt.astimezone(IST)
                hour_of_day = dt_ist.hour
                day_of_week = dt_ist.weekday()
            else:
                now_ist = datetime.now(IST)
                hour_of_day = now_ist.hour
                day_of_week = now_ist.weekday()
        except Exception:
            now_ist = datetime.now(IST)
            hour_of_day = now_ist.hour
            day_of_week = now_ist.weekday()

        is_weekend = 1 if day_of_week >= 5 else 0
        is_peak_hours = 1 if hour_of_day in PEAK_HOURS else 0

        # Worker age in days
        try:
            worker_created = worker.get("created_at", "")
            if worker_created:
                wd = datetime.fromisoformat(str(worker_created).replace("Z", "+00:00"))
                wd_ist = wd.astimezone(IST)
                worker_days_registered = max(0, (datetime.now(IST) - wd_ist).days)
            else:
                worker_days_registered = 90
        except Exception:
            worker_days_registered = 90

        features = [
            float(layer1_score),                                          # fraud_score_layer1
            float(claim.get("payout_amount", 200.0)),                    # payout_amount
            float(claim.get("disrupted_hours", 2.0)),                    # disrupted_hours
            float(hour_of_day),                                           # hour_of_day
            float(day_of_week),                                           # day_of_week
            float(worker_claim_count_30d),                                # worker_claim_count_30d
            float(zone_claim_count_hour),                                 # zone_claim_count_hour
            float(worker_days_registered),                                # worker_days_registered
            float(zone.get("risk_multiplier", 1.0)),                     # zone_risk_multiplier
            float(trigger.get("severity", 0.5)),                         # trigger_severity
            float(is_weekend),                                            # is_weekend
            float(is_peak_hours),                                         # is_peak_hours
        ]

        return features

    # ─────────────────────────────────────────────────────────────────────────
    # Scoring
    # ─────────────────────────────────────────────────────────────────────────

    @classmethod
    def _score_sync(cls, features: list) -> float:
        """
        Synchronous scoring — run in executor to avoid blocking the event loop.

        Isolation Forest decision_function returns:
        - Positive values → normal (far from decision boundary)
        - Negative values → anomalous (close to / beyond boundary)

        We convert to fraud probability [0, 1] using a scaled sigmoid:
            fraud_prob = 1 / (1 + exp(raw_score * 3))

        Scaling factor 3: stretches the sigmoid so that:
        -1.0 → 0.95 (very fraudulent)
         0.0 → 0.50 (uncertain)
        +1.0 → 0.05 (very clean)
        """
        X = cls._scaler.transform([features])
        raw_score = float(cls._model.decision_function(X)[0])
        fraud_probability = 1.0 / (1.0 + np.exp(raw_score * 3.0))
        return round(float(fraud_probability), 3)

    @classmethod
    async def score(
        cls,
        claim: dict,
        worker: dict,
        trigger: dict,
        zone: dict,
        layer1_score: float,
        worker_claim_count_30d: int = 2,
        zone_claim_count_hour: int = 1,
        fallback_score: float = 0.30,
    ) -> float:
        """
        Score a claim for fraud using the Isolation Forest model.

        Has a 2-second timeout. If the model is unavailable or times out,
        returns fallback_score (neutral) so claim processing continues.

        Args:
            claim:                  Claim record
            worker:                 Worker record
            trigger:                Trigger event record
            zone:                   Zone record
            layer1_score:           Rule-engine fraud score (used as a feature)
            worker_claim_count_30d: 30-day claim count for this worker
            zone_claim_count_hour:  Concurrent claims in zone/hour
            fallback_score:         Score to use if model unavailable

        Returns:
            float: Fraud probability [0, 1]
        """
        if not cls.is_loaded():
            print("[IFScorer] Model not loaded — falling back to Layer 1")
            return fallback_score

        try:
            features = cls._build_feature_vector(
                claim, worker, trigger, zone, layer1_score,
                worker_claim_count_30d, zone_claim_count_hour
            )

            # Run CPU-bound scoring in thread pool with 2s timeout
            loop = asyncio.get_event_loop()
            score = await asyncio.wait_for(
                loop.run_in_executor(None, cls._score_sync, features),
                timeout=2.0,
            )
            return score

        except asyncio.TimeoutError:
            print("[IFScorer] ⚠️ Scoring timed out (>2s) — falling back to Layer 1")
            return fallback_score

        except Exception as e:
            print(f"[IFScorer] ⚠️ Scoring error: {e} — falling back to Layer 1")
            return fallback_score
