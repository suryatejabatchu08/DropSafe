import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from routers.premium import router as premium_router
from routers.triggers import router as triggers_router
from routers.fraud import router as fraud_router
from routers.whatsapp import router as whatsapp_router
from routers.admin import router as admin_router
from routers.payouts import router as payouts_router
from routers.dashboard import router as dashboard_router
from routers.zones import router as zones_router
from routers.webhooks import router as webhooks_router
from routers.ml import router as ml_router
from routers.analytics import router as analytics_router
from routers.worker import router as worker_router
from routers.demo import router as demo_router
from routers.system import router as system_router
from database import init_supabase, get_worker_count
from scheduler import start_scheduler, stop_scheduler


MODELS_DIR = os.path.join(os.path.dirname(__file__), "models")
MODEL_PATH = os.path.join(MODELS_DIR, "isolation_forest.pkl")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Lifespan context manager for startup and shutdown events.
    """
    # Startup
    print("[STARTUP] Initializing DropSafe backend...")
    try:
        init_supabase()
        worker_count = await get_worker_count()
        print(f"[OK] Supabase connected. Workers in system: {worker_count}")
    except Exception as e:
        print(f"[ERROR] Failed to connect to Supabase: {e}")
        print("[WARN] Backend will continue but database operations will fail.")

    try:
        start_scheduler()
        print("[OK] Scheduler started successfully")
    except Exception as e:
        print(f"[ERROR] Failed to start scheduler: {e}")
        print("[WARN] Scheduled jobs will not run.")

    # ── Isolation Forest startup ──────────────────────────────────────────
    try:
        from services.isolation_forest_scorer import IsolationForestScorer
        from services.isolation_forest_trainer import IsolationForestTrainer

        if os.path.exists(MODEL_PATH):
            # Model exists — load from disk
            loaded = IsolationForestScorer.load_model()
            if loaded:
                print("[OK] Isolation Forest model loaded ✅")
            else:
                print("[WARN] Model file exists but failed to load — retraining...")
                await IsolationForestTrainer.train()
                IsolationForestScorer.load_model()
                print("[OK] Isolation Forest retrained and loaded ✅")
        else:
            # No model — train on synthetic data
            print("[STARTUP] No Isolation Forest model found — training on synthetic data...")
            os.makedirs(MODELS_DIR, exist_ok=True)
            await IsolationForestTrainer.train()
            IsolationForestScorer.load_model()
            print("[OK] Isolation Forest trained and loaded ✅")

    except Exception as e:
        print(f"[WARN] Isolation Forest startup failed: {e}")
        print("[WARN] Layer 2 fraud detection will be disabled (Layer 1 only)")

    # ── XGBoost Premium Model startup ─────────────────────────────────────
    try:
        from services.xgboost_premium import XGBoostPremiumModel

        print("[STARTUP] Initializing XGBoost premium model...")
        if not XGBoostPremiumModel.load():
            print("[STARTUP] Training XGBoost model on synthetic data...")
            XGBoostPremiumModel.train()
            XGBoostPremiumModel.load()
        print("[OK] XGBoost premium model loaded ✅")

    except Exception as e:
        print(f"[WARN] XGBoost startup failed: {e}")
        print("[WARN] Dynamic premium adjustment will use rule-based only")

    print("[STARTUP] DropSafe backend ready! 🚀")

    yield

    # Shutdown
    print("[SHUTDOWN] Stopping DropSafe backend...")
    try:
        stop_scheduler()
        print("[OK] Scheduler stopped")
    except Exception as e:
        print(f"[WARN] Error stopping scheduler: {e}")
    print("[SHUTDOWN] DropSafe backend stopped gracefully")


app = FastAPI(
    title="DropSafe",
    version="3.0.0",
    description="AI-powered parametric income insurance for Q-Commerce delivery partners",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://dropsafe-sable.vercel.app",
    ],
    allow_origin_regex=r"^http://localhost:\d+$",
    # Allow localhost dev ports and production Vercel domain
    allow_headers=["*"],
    allow_methods=["*"],
    allow_credentials=False,
)

# Phase 1 & 2 routers
app.include_router(premium_router)
app.include_router(triggers_router)
app.include_router(fraud_router)
app.include_router(whatsapp_router)
app.include_router(admin_router)
app.include_router(payouts_router)
app.include_router(dashboard_router)
app.include_router(zones_router)
app.include_router(webhooks_router)

# Phase 3 routers
app.include_router(ml_router)
app.include_router(analytics_router)
app.include_router(worker_router)
app.include_router(demo_router)
app.include_router(system_router)


@app.get("/health")
async def health():
    """
    Health check endpoint.
    Returns system status, worker count, and ML model status.
    """
    from services.isolation_forest_scorer import IsolationForestScorer

    worker_count = await get_worker_count()
    return {
        "status": "ok",
        "project": "DropSafe",
        "version": "3.0.0",
        "total_workers": worker_count,
        "database": "connected" if worker_count >= 0 else "error",
        "ml_model_loaded": IsolationForestScorer.is_loaded(),
        "phase": "Phase 3 — Scale & Optimise",
    }
