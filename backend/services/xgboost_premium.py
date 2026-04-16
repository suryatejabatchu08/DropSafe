"""
DropSafe XGBoost Premium Model
ML-based dynamic premium adjustment for Q-Commerce delivery workers
"""

import os
import joblib
import numpy as np
from datetime import datetime, timedelta
import xgboost as xgb
import pytz

IST = pytz.timezone("Asia/Kolkata")

MODELS_DIR = os.path.join(os.path.dirname(__file__), "..", "models")
XGBOOST_MODEL_PATH = os.path.join(MODELS_DIR, "xgboost_premium.pkl")
XGBOOST_METADATA_PATH = os.path.join(MODELS_DIR, "xgboost_metadata.json")


class XGBoostPremiumModel:
    """
    XGBoost regressor for dynamic premium adjustment.

    Features:
    - zone_risk: Zone risk multiplier (0.75–1.60)
    - rainfall_7d: Forecasted rainfall in mm for next 7 days
    - temp_avg: Average temperature (°C)
    - aqi_avg: Average AQI
    - season_index: Seasonal multiplier (1.0–1.35)
    - claim_rate: Historical claim rate (0–1)

    Target: Premium adjustment factor (-0.25 to +0.25)
    """

    _model = None
    _loaded = False

    @staticmethod
    def generate_training_data(n: int = 500) -> tuple:
        """
        Generate synthetic training data with realistic patterns.

        Args:
            n: Number of samples to generate

        Returns:
            (X, y) where X is features array, y is adjustment targets
        """
        np.random.seed(42)

        X = []
        y = []

        for _ in range(n):
            # Features
            zone_risk = np.random.uniform(0.75, 1.60)
            rainfall_7d = np.random.uniform(0, 100)
            temp_avg = np.random.uniform(25, 48)
            aqi_avg = np.random.uniform(50, 500)
            season_index = np.random.choice([1.0, 1.15, 1.30, 1.35])
            claim_rate = np.random.uniform(0, 0.5)

            # Target: Premium adjustment based on risk factors
            # High rainfall → increase premium
            # High AQI → increase premium
            # High temp → increase premium (heat reduces delivery volume)
            # High claim rate → increase premium
            # Seasonal → already captured in multiplier

            adjustment = (
                (rainfall_7d / 100) * 0.15 +           # Rainfall impact
                (max(temp_avg - 35, 0) / 13) * 0.10 +   # Heat impact
                (max(aqi_avg - 200, 0) / 300) * 0.15 +  # AQI impact
                (claim_rate * 0.10) +                    # Claim history
                (zone_risk - 1.0) * 0.20 +              # Zone risk
                (season_index - 1.0) * 0.15 -           # Seasonal already priced
                0.20                                     # Base offset
            )

            adjustment = np.clip(adjustment, -0.25, 0.25)

            X.append([zone_risk, rainfall_7d, temp_avg, aqi_avg, season_index, claim_rate])
            y.append(adjustment)

        return np.array(X), np.array(y)

    @classmethod
    def train(cls) -> dict:
        """
        Train XGBoost model on synthetic data.

        Returns:
            dict with training metadata
        """
        try:
            print("[XGBoost] Generating training data...")
            X, y = cls.generate_training_data(500)

            print("[XGBoost] Training XGBoost model...")
            model = xgb.XGBRegressor(
                n_estimators=100,
                max_depth=4,
                learning_rate=0.1,
                random_state=42,
                objective='reg:squarederror',
                tree_method='hist'
            )
            model.fit(X, y)

            # Save model
            os.makedirs(MODELS_DIR, exist_ok=True)
            joblib.dump(model, XGBOOST_MODEL_PATH)

            # Save metadata
            import json
            metadata = {
                "model_type": "XGBoost",
                "trained_at": datetime.now(IST).isoformat(),
                "samples": 500,
                "synthetic_samples": 500,
                "real_samples": 0,
                "features": [
                    "zone_risk",
                    "rainfall_7d_mm",
                    "temp_avg_c",
                    "aqi_avg",
                    "season_index",
                    "claim_rate"
                ],
                "target_range": [-0.25, 0.25],
                "n_estimators": 100,
                "max_depth": 4,
                "learning_rate": 0.1,
            }

            with open(XGBOOST_METADATA_PATH, "w") as f:
                json.dump(metadata, f, indent=2)

            print("[XGBoost] ✅ XGBoost premium model trained and saved")
            return {
                "status": "success",
                "model_type": "XGBoost",
                "samples": 500,
                "n_estimators": 100,
                "trained_at": metadata["trained_at"]
            }

        except Exception as e:
            print(f"[XGBoost] ❌ Training failed: {e}")
            raise

    @classmethod
    def load(cls) -> bool:
        """Load model from disk."""
        try:
            if not os.path.exists(XGBOOST_MODEL_PATH):
                print("[XGBoost] Model not found, will train on demand")
                return False

            cls._model = joblib.load(XGBOOST_MODEL_PATH)
            cls._loaded = True
            print("[XGBoost] ✅ XGBoost model loaded from disk")
            return True

        except Exception as e:
            print(f"[XGBoost] ❌ Failed to load model: {e}")
            cls._loaded = False
            return False

    @classmethod
    def is_loaded(cls) -> bool:
        """Check if model is loaded."""
        return cls._loaded and cls._model is not None

    @classmethod
    def predict(
        cls,
        zone_risk: float,
        rainfall_7d: float,
        temp_avg: float,
        aqi_avg: float,
        season_index: float,
        claim_rate: float
    ) -> dict:
        """
        Predict premium adjustment.

        Args:
            zone_risk: Zone risk multiplier
            rainfall_7d: 7-day rainfall forecast in mm
            temp_avg: Average temperature in °C
            aqi_avg: Average AQI
            season_index: Seasonal multiplier
            claim_rate: Historical claim rate

        Returns:
            dict with adjustment, multiplier, and features
        """
        try:
            if not cls.is_loaded():
                # Train if not loaded
                cls.train()
                cls.load()

            X = np.array([[
                zone_risk,
                rainfall_7d,
                temp_avg,
                aqi_avg,
                season_index,
                claim_rate
            ]])

            raw_adjustment = float(cls._model.predict(X)[0])
            raw_adjustment = np.clip(raw_adjustment, -0.25, 0.25)

            # Convert adjustment to multiplier (1.0 = no change)
            multiplier = 1.0 + raw_adjustment

            return {
                "model": "XGBoost_v1",
                "features": {
                    "zone_risk": round(zone_risk, 2),
                    "rainfall_7d_mm": round(rainfall_7d, 1),
                    "temp_avg_c": round(temp_avg, 1),
                    "aqi_avg": round(aqi_avg, 1),
                    "season_index": round(season_index, 2),
                    "claim_rate": round(claim_rate, 3),
                },
                "raw_adjustment": round(raw_adjustment, 3),
                "final_multiplier": round(multiplier, 3),
            }

        except Exception as e:
            print(f"[XGBoost] ❌ Prediction error: {e}")
            # Fallback: no adjustment
            return {
                "model": "XGBoost_v1",
                "error": str(e),
                "raw_adjustment": 0.0,
                "final_multiplier": 1.0,
            }
