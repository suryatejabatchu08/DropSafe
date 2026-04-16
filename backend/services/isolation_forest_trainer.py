"""
DropSafe — Isolation Forest Trainer (Fraud Detection Layer 2)

Anti-bias mechanisms:
1. RobustScaler (median/IQR) — outliers don't distort feature scaling
2. Dynamic contamination — calibrated to actual fraud rate, not hardcoded
3. One-class training strategy — balance training set (5:1 legit:fraud max)
4. Non-overlapping synthetic populations — fraud features cleanly separated
5. Bias metrics logged — anomaly_rate, FPR tracked after every train
"""

import os
import json
import time
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from typing import Optional, Tuple

import joblib
from sklearn.ensemble import IsolationForest
from sklearn.preprocessing import RobustScaler

import pytz

IST = pytz.timezone("Asia/Kolkata")

# Paths (relative to backend/)
MODELS_DIR = os.path.join(os.path.dirname(__file__), "..", "models")
MODEL_PATH = os.path.join(MODELS_DIR, "isolation_forest.pkl")
SCALER_PATH = os.path.join(MODELS_DIR, "scaler.pkl")
METADATA_PATH = os.path.join(MODELS_DIR, "model_metadata.json")

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


class IsolationForestTrainer:
    """
    Trains the Isolation Forest anomaly detection model on claim data.

    Anti-bias design:
    - Uses RobustScaler (not StandardScaler) to resist outlier distortion
    - Calibrates contamination dynamically from data
    - Balances training set at max 5:1 ratio (legit:fraud)
    - Synthetic data has clearly separated fraud/legit feature distributions
    """

    # ─────────────────────────────────────────────────────────────────────────
    # Feature Preparation
    # ─────────────────────────────────────────────────────────────────────────

    @staticmethod
    def prepare_features(claims_df: pd.DataFrame) -> pd.DataFrame:
        """
        Extract the 12-feature vector from a claims DataFrame.

        Expected columns in claims_df:
            fraud_score, payout_amount, disrupted_hours, created_at,
            worker_claim_count_30d, zone_claim_count_hour,
            worker_days_registered, zone_risk_multiplier,
            trigger_severity
        """
        df = claims_df.copy()

        # DEBUG: Print input columns
        print(f"[prepare_features] Input DataFrame shape: {df.shape}")
        print(f"[prepare_features] Input columns before processing: {list(df.columns)}")

        # Parse timestamps → IST
        if "created_at" in df.columns:
            df["created_at"] = pd.to_datetime(df["created_at"], errors="coerce", utc=True)
            df["created_at"] = df["created_at"].dt.tz_convert(IST)
            df["hour_of_day"] = df["created_at"].dt.hour
            df["day_of_week"] = df["created_at"].dt.dayofweek
            df["is_weekend"] = (df["day_of_week"] >= 5).astype(int)
        else:
            df["hour_of_day"] = 12
            df["day_of_week"] = 0
            df["is_weekend"] = 0

        # Peak hours: lunch (12-13) and dinner (19-21)
        peak_hours = {12, 13, 19, 20, 21}
        df["is_peak_hours"] = df["hour_of_day"].apply(
            lambda h: 1 if h in peak_hours else 0
        )

        # Rename to standard names if needed
        rename_map = {
            "fraud_score": "fraud_score_layer1",
        }
        df = df.rename(columns=rename_map)

        # Drop the old 'fraud_score' column if it exists (after rename, it shouldn't, but be safe)
        df = df.drop(columns=["fraud_score"], errors="ignore")

        # Fill defaults for missing columns
        defaults = {
            "fraud_score_layer1": 0.1,
            "payout_amount": 200.0,
            "disrupted_hours": 2.0,
            "worker_claim_count_30d": 2,
            "zone_claim_count_hour": 1,
            "worker_days_registered": 90,
            "zone_risk_multiplier": 1.0,
            "trigger_severity": 0.5,
        }
        for col, val in defaults.items():
            if col not in df.columns:
                df[col] = val

        # Remove any duplicate columns (keep only the expected FEATURE_NAMES)
        # Drop old fraud_score if it still exists
        df = df.drop(columns=["fraud_score"], errors="ignore")

        # Handle any case where columns might be duplicated
        # Select only the columns in FEATURE_NAMES, in that order
        result = df[FEATURE_NAMES].fillna(0.0)

        # Verify no duplicates in result
        if len(result.columns) != len(set(result.columns)):
            print(f"[WARNING] Duplicate columns detected! Fixing...")
            result = result.loc[:, ~result.columns.duplicated(keep='first')]

        print(f"[prepare_features] Output shape: {result.shape}")
        print(f"[prepare_features] Output columns: {list(result.columns)}")

        return result

    # ─────────────────────────────────────────────────────────────────────────
    # Training Set Balancing
    # ─────────────────────────────────────────────────────────────────────────

    @staticmethod
    def balance_training_set(claims_df: pd.DataFrame) -> pd.DataFrame:
        """
        Balance training data to avoid majority-class bias.

        Strategy:
        - Use ALL rejected claims (known fraud) — minority gets full representation
        - Cap legitimate claims at max 5× fraud count
        - Include 50% of 'review' claims (uncertain — sample to prevent bias)

        This prevents the model from only learning the dense legit cluster
        and missing the sparse fraud patterns.
        """
        if "status" not in claims_df.columns:
            return claims_df  # Synthetic data — already balanced

        legit = claims_df[claims_df["status"] == "auto_approved"]
        fraud = claims_df[claims_df["status"] == "rejected"]
        review = claims_df[claims_df["status"] == "review"]

        # If no fraud examples exist, return as-is (purely unsupervised)
        if len(fraud) == 0:
            print("[Trainer] No labeled fraud samples — using all data unsupervised")
            return claims_df

        # Cap legit at 5× fraud count to limit imbalance (5:1 is the sweet spot)
        max_legit = max(len(fraud) * 5, 50)
        if len(legit) > max_legit:
            legit = legit.sample(n=max_legit, random_state=42)
            print(
                f"[Trainer] Balanced: capped legit at {max_legit} "
                f"(was {len(claims_df[claims_df['status'] == 'auto_approved'])})"
            )

        # Include 50% of review claims (uncertain)
        if len(review) > 0:
            review = review.sample(frac=0.5, random_state=42)

        balanced = pd.concat([legit, fraud, review], ignore_index=True)
        print(
            f"[Trainer] Balanced training set: {len(legit)} legit, "
            f"{len(fraud)} fraud, {len(review)} review → {len(balanced)} total"
        )
        return balanced

    # ─────────────────────────────────────────────────────────────────────────
    # Contamination Estimation
    # ─────────────────────────────────────────────────────────────────────────

    @staticmethod
    def estimate_contamination(claims_df: pd.DataFrame) -> float:
        """
        Dynamically estimate contamination (expected anomaly fraction).

        Hardcoded contamination causes bias:
        - Too high → model flags too many legit claims (false positives)
        - Too low → fraud slips through (false negatives)

        We estimate from real labels if available, otherwise use 0.10.
        Add 5% buffer to handle label noise in 'review' claims.
        Clamp: min=0.05 (model must flag something), max=0.25 (sanity cap).
        """
        if "status" in claims_df.columns:
            total = len(claims_df)
            fraud_count = (claims_df["status"] == "rejected").sum()

            if total > 0 and fraud_count > 0:
                observed_rate = fraud_count / total
                # 5% buffer for unlabeled fraud in 'review' bucket
                contamination = float(np.clip(observed_rate + 0.05, 0.05, 0.25))
                print(
                    f"[Trainer] Contamination estimated: {contamination:.3f} "
                    f"(observed fraud rate: {observed_rate:.3f})"
                )
                return contamination

        # No labels — conservative default (lower → fewer false positives)
        print("[Trainer] No fraud labels found — using default contamination: 0.10")
        return 0.10

    # ─────────────────────────────────────────────────────────────────────────
    # Synthetic Data Generation
    # ─────────────────────────────────────────────────────────────────────────

    @staticmethod
    def generate_synthetic_data(n: int = 200) -> pd.DataFrame:
        """
        Generate realistic synthetic claim data for training bootstrap.

        Populations are CLEANLY SEPARATED to avoid training on ambiguous data:
        - 85% legitimate (n_legit = 170): low fraud scores, working hours, established workers
        - 15% fraudulent (n_fraud = 30): high fraud scores, off-hours, brand new workers

        Key anti-overlap design:
        - Legit payout: ₹80–₹400   |  Fraud payout: ₹600–₹1,280
        - Legit hours:  8 AM–10 PM  |  Fraud hours:  0 AM–5 AM
        - Legit days:   30–365      |  Fraud days:   1–7
        - Legit freq:   1–5/30d     |  Fraud freq:   9–15/30d
        - Legit score:  0.05–0.35   |  Fraud score:  0.60–0.95

        seed=42 for full reproducibility.
        """
        rng = np.random.default_rng(42)

        n_fraud = max(int(n * 0.15), 30)
        n_legit = n - n_fraud

        # ── LEGITIMATE CLAIMS (85%) ────────────────────────────────────────
        legit = {
            "fraud_score_layer1": rng.uniform(0.05, 0.35, n_legit),
            "payout_amount": rng.uniform(80.0, 400.0, n_legit),  # ₹80–₹400
            "disrupted_hours": rng.uniform(1.0, 5.5, n_legit),
            "hour_of_day": rng.integers(8, 23, n_legit),  # 8 AM–10 PM
            "day_of_week": rng.integers(0, 7, n_legit),
            "worker_claim_count_30d": rng.integers(1, 6, n_legit),  # 1–5
            "zone_claim_count_hour": rng.integers(1, 8, n_legit),
            "worker_days_registered": rng.integers(30, 366, n_legit),  # Established
            "zone_risk_multiplier": rng.uniform(0.8, 1.5, n_legit),
            "trigger_severity": rng.uniform(0.3, 0.8, n_legit),
            "is_weekend": rng.integers(0, 2, n_legit),
            "is_peak_hours": rng.choice([0, 1], n_legit, p=[0.35, 0.65]),
            "status": ["auto_approved"] * n_legit,
        }

        # ── FRAUDULENT CLAIMS (15%) ────────────────────────────────────────
        # Key fraud signals: off-hours, new workers, high payout, high freq
        fraud = {
            "fraud_score_layer1": rng.uniform(0.60, 0.95, n_fraud),  # High (no overlap)
            "payout_amount": rng.uniform(600.0, 1280.0, n_fraud),   # ₹600–₹1280 (no overlap)
            "disrupted_hours": rng.uniform(5.5, 8.0, n_fraud),       # Maxed out
            "hour_of_day": rng.integers(0, 6, n_fraud),              # 0–5 AM only
            "day_of_week": rng.integers(0, 7, n_fraud),
            "worker_claim_count_30d": rng.integers(9, 16, n_fraud),  # 9–15 (no overlap)
            "zone_claim_count_hour": rng.integers(15, 30, n_fraud),  # Cluster pattern
            "worker_days_registered": rng.integers(1, 8, n_fraud),   # 1–7 days (no overlap)
            "zone_risk_multiplier": rng.uniform(1.5, 2.0, n_fraud),  # High-risk zones
            "trigger_severity": rng.uniform(0.85, 1.0, n_fraud),     # Always max severity
            "is_weekend": rng.integers(0, 2, n_fraud),
            "is_peak_hours": np.zeros(n_fraud, dtype=int),           # Never peak hours
            "status": ["rejected"] * n_fraud,
        }

        legit_df = pd.DataFrame(legit)
        fraud_df = pd.DataFrame(fraud)

        combined = pd.concat([legit_df, fraud_df], ignore_index=True)

        # Shuffle to avoid any ordering bias during tree construction
        combined = combined.sample(frac=1.0, random_state=42).reset_index(drop=True)

        print(
            f"[Trainer] Generated synthetic data: {n_legit} legit + {n_fraud} fraud "
            f"= {len(combined)} samples"
        )
        return combined

    # ─────────────────────────────────────────────────────────────────────────
    # Model Evaluation (Bias Detection)
    # ─────────────────────────────────────────────────────────────────────────

    @staticmethod
    def evaluate_bias_metrics(
        model: IsolationForest, X: np.ndarray, labels: Optional[pd.Series] = None
    ) -> dict:
        """
        Compute bias indicators post-training.
        Uses Precision/Recall (not Accuracy) — accuracy is misleading for imbalanced data.

        Stored in model_metadata.json alongside the .pkl files.
        """
        scores = model.decision_function(X)
        predictions = model.predict(X)  # -1=anomaly, 1=normal

        anomaly_rate = float((predictions == -1).mean())

        metrics = {
            "anomaly_rate_train": round(anomaly_rate, 3),
            "score_mean": round(float(scores.mean()), 4),
            "score_std": round(float(scores.std()), 4),
            "score_p5": round(float(np.percentile(scores, 5)), 4),
            "score_p95": round(float(np.percentile(scores, 95)), 4),
            "false_positive_rate": None,
            "precision": None,
            "recall": None,
        }

        if labels is not None and "status" in labels.columns if hasattr(labels, "columns") else False:
            pass  # handled below

        if labels is not None and hasattr(labels, "values"):
            from sklearn.metrics import precision_score, recall_score

            preds_binary = (predictions == -1).astype(int)
            fraud_labels = (labels == "rejected").astype(int).values

            if fraud_labels.sum() > 0:
                metrics["precision"] = round(
                    float(precision_score(fraud_labels, preds_binary, zero_division=0)), 3
                )
                metrics["recall"] = round(
                    float(recall_score(fraud_labels, preds_binary, zero_division=0)), 3
                )
                # FPR = legit claims wrongly flagged as fraud
                legit_mask = fraud_labels == 0
                fpr = float(
                    (preds_binary[legit_mask] == 1).sum() / legit_mask.sum()
                ) if legit_mask.sum() > 0 else 0.0
                metrics["false_positive_rate"] = round(fpr, 3)

        return metrics

    # ─────────────────────────────────────────────────────────────────────────
    # Main Train Function
    # ─────────────────────────────────────────────────────────────────────────

    @staticmethod
    async def train() -> dict:
        """
        Train the Isolation Forest model.

        Flow:
        1. Fetch real claims from Supabase
        2. If < 50 real claims → augment with synthetic data
        3. Balance training set (5:1 legit:fraud max)
        4. Estimate contamination dynamically
        5. Fit IsolationForest with RobustScaler
        6. Evaluate bias metrics
        7. Save model + scaler + metadata to models/

        Returns:
            {samples_used, training_time_sec, model_version, contamination, metrics}
        """
        t_start = time.time()
        print("\n[IsolationForestTrainer] Starting training...")

        try:
            from database import get_supabase

            supabase = get_supabase()

            # ── STEP 1: Fetch real claims ──────────────────────────────────
            response = (
                supabase.table("claims")
                .select(
                    "fraud_score, payout_amount, disrupted_hours, created_at, "
                    "fraud_flags, worker_id, zone_id, trigger_event_id, status"
                )
                .order("created_at", desc=True)
                .limit(2000)
                .execute()
            )

            real_claims = response.data or []
            print(f"[Trainer] Fetched {len(real_claims)} real claims from Supabase")

            # ── STEP 2: Enrich with worker/zone features ───────────────────
            real_df = None
            if len(real_claims) >= 10:
                real_df = await IsolationForestTrainer._enrich_claims(
                    supabase, real_claims
                )

            # ── STEP 3: Decide training source ────────────────────────────
            if real_df is not None and len(real_df) >= 50:
                print(
                    f"[Trainer] Using real data ({len(real_df)} claims) for training"
                )
                training_df = real_df
                used_synthetic = False
            else:
                real_count = len(real_df) if real_df is not None else 0
                print(
                    f"[Trainer] Only {real_count} real claims — "
                    f"augmenting with synthetic data"
                )
                synth_df = IsolationForestTrainer.generate_synthetic_data(n=200)
                if real_df is not None and len(real_df) > 0:
                    # Merge real + synthetic (real claims get equal feature columns)
                    synth_df = synth_df.drop(columns=["status"], errors="ignore")
                    training_df = pd.concat([real_df, synth_df], ignore_index=True)
                else:
                    training_df = synth_df
                used_synthetic = True

            # ── STEP 4: Balance training set ──────────────────────────────
            training_df = IsolationForestTrainer.balance_training_set(training_df)
            n_samples = len(training_df)

            # ── STEP 5: Estimate contamination ────────────────────────────
            contamination = IsolationForestTrainer.estimate_contamination(training_df)

            # ── STEP 6: Prepare feature matrix ────────────────────────────
            labels = training_df.get("status", None)
            features_df = IsolationForestTrainer.prepare_features(training_df)

            # DEBUG: Print feature details
            print(f"[Trainer] Features DataFrame shape: {features_df.shape}")
            print(f"[Trainer] Features DataFrame columns: {list(features_df.columns)}")
            print(f"[Trainer] Expected FEATURE_NAMES ({len(FEATURE_NAMES)}): {FEATURE_NAMES}")

            X = features_df.values.astype(float)
            print(f"[Trainer] X array shape: {X.shape}")

            # ── STEP 7: Scale with RobustScaler ───────────────────────────
            # RobustScaler uses median + IQR → fraud outliers don't distort scaling
            scaler = RobustScaler(quantile_range=(10.0, 90.0))
            print(f"[Trainer] Fitting RobustScaler on X with shape {X.shape}...")
            X_scaled = scaler.fit_transform(X)
            print(f"[Trainer] Scaler fitted successfully. n_features_in_: {scaler.n_features_in_}")

            # ── STEP 8: Fit Isolation Forest ───────────────────────────────
            model = IsolationForest(
                n_estimators=100,
                contamination=contamination,
                max_samples="auto",
                random_state=42,
                n_jobs=-1,  # Use all CPU cores
                bootstrap=False,  # Subsampling without replacement = more stable
            )
            model.fit(X_scaled)

            # ── STEP 9: Evaluate bias metrics ─────────────────────────────
            bias_metrics = IsolationForestTrainer.evaluate_bias_metrics(
                model, X_scaled, labels
            )

            # ── STEP 10: Save model + scaler ──────────────────────────────
            os.makedirs(MODELS_DIR, exist_ok=True)
            joblib.dump(model, MODEL_PATH)
            joblib.dump(scaler, SCALER_PATH)

            training_time = round(time.time() - t_start, 2)
            model_version = f"IsolationForest_v1_{datetime.now(IST).strftime('%Y%m%d_%H%M')}"

            # ── STEP 11: Save metadata ─────────────────────────────────────
            metadata = {
                "model_version": model_version,
                "trained_at": datetime.now(IST).isoformat(),
                "samples_used": n_samples,
                "used_synthetic": used_synthetic,
                "contamination": contamination,
                "n_estimators": 100,
                "scaler": "RobustScaler(quantile_range=(10,90))",
                "feature_names": FEATURE_NAMES,
                "training_time_sec": training_time,
                "bias_metrics": bias_metrics,
            }
            with open(METADATA_PATH, "w") as f:
                json.dump(metadata, f, indent=2)

            print(
                f"[Trainer] ✅ Isolation Forest trained on {n_samples} samples "
                f"in {training_time}s | contamination={contamination:.3f}"
            )
            print(f"[Trainer] Bias metrics: {bias_metrics}")
            print(f"[Trainer] Model saved to {MODEL_PATH}")

            return {
                "samples_used": n_samples,
                "training_time_sec": training_time,
                "model_version": model_version,
                "contamination": contamination,
                "used_synthetic": used_synthetic,
                "bias_metrics": bias_metrics,
            }

        except Exception as e:
            import traceback
            print(f"[Trainer] ❌ Training failed: {e}")
            traceback.print_exc()
            raise

    # ─────────────────────────────────────────────────────────────────────────
    # Claim Enrichment (add worker/zone features from Supabase)
    # ─────────────────────────────────────────────────────────────────────────

    @staticmethod
    async def _enrich_claims(supabase, claims: list) -> Optional[pd.DataFrame]:
        """
        Enrich raw claim records with worker/zone features needed for training.
        Fetches worker registration date, zone risk multiplier, and
        computes per-worker claim frequency over 30 days.
        """
        try:
            df = pd.DataFrame(claims)

            # Rename fraud_score → fraud_score_layer1 and drop the old column
            if "fraud_score" in df.columns:
                df["fraud_score_layer1"] = df["fraud_score"]
                df = df.drop(columns=["fraud_score"])

            # Get all unique worker IDs + zone IDs
            worker_ids = df["worker_id"].dropna().unique().tolist()
            zone_ids = df["zone_id"].dropna().unique().tolist()

            # Fetch workers
            workers_resp = (
                supabase.table("workers")
                .select("id, created_at")
                .in_("id", worker_ids[:100])  # Supabase limit
                .execute()
            )
            workers_map = {
                w["id"]: w for w in (workers_resp.data or [])
            }

            # Fetch zones
            zones_resp = (
                supabase.table("zones")
                .select("id, risk_multiplier")
                .in_("id", zone_ids[:100])
                .execute()
            )
            zones_map = {
                z["id"]: z for z in (zones_resp.data or [])
            }

            # Compute 30-day claim counts per worker
            now = datetime.now(IST)
            thirty_days_ago = (now - timedelta(days=30)).isoformat()
            freq_resp = (
                supabase.table("claims")
                .select("worker_id, created_at")
                .gte("created_at", thirty_days_ago)
                .execute()
            )
            freq_data = freq_resp.data or []
            freq_map: dict = {}
            for row in freq_data:
                wid = row.get("worker_id")
                if wid:
                    freq_map[wid] = freq_map.get(wid, 0) + 1

            # Add enriched columns
            def get_days_since(worker_id):
                w = workers_map.get(worker_id, {})
                ca = w.get("created_at")
                if ca:
                    try:
                        dt = pd.to_datetime(ca, utc=True).tz_convert(IST)
                        return max(0, (now - dt).days)
                    except Exception:
                        pass
                return 90  # Default

            df["worker_days_registered"] = df["worker_id"].apply(get_days_since)
            df["zone_risk_multiplier"] = df["zone_id"].apply(
                lambda zid: float(zones_map.get(zid, {}).get("risk_multiplier", 1.0))
            )
            df["worker_claim_count_30d"] = df["worker_id"].apply(
                lambda wid: freq_map.get(wid, 0)
            )

            # trigger_severity from fraud_flags if available
            def get_severity(flags):
                if isinstance(flags, dict):
                    return float(flags.get("trigger_severity", 0.5))
                return 0.5

            if "fraud_flags" in df.columns:
                df["trigger_severity"] = df["fraud_flags"].apply(get_severity)
            else:
                df["trigger_severity"] = 0.5

            df["zone_claim_count_hour"] = 1  # Default (hard to compute retroactively)

            return df

        except Exception as e:
            print(f"[Trainer] Warning: Claim enrichment failed: {e}")
            return None
