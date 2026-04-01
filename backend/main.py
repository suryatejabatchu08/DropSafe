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
from database import init_supabase, get_worker_count
from scheduler import start_scheduler, stop_scheduler


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
    version="0.1.0",
    description="AI-powered parametric income insurance for Q-Commerce delivery partners",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://dropsafe-ashy.vercel.app",
    ],
    allow_origin_regex=r"^http://localhost:\d+$",
    # Allow localhost dev ports and production Vercel domain
    allow_headers=["*"],
    allow_methods=["*"],
    allow_credentials=False,
)

app.include_router(premium_router)
app.include_router(triggers_router)
app.include_router(fraud_router)
app.include_router(whatsapp_router)
app.include_router(admin_router)
app.include_router(payouts_router)
app.include_router(dashboard_router)
app.include_router(zones_router)
app.include_router(webhooks_router)


@app.get("/health")
async def health():
    """
    Health check endpoint.
    Returns system status and worker count from Supabase.
    """
    worker_count = await get_worker_count()
    return {
        "status": "ok",
        "project": "DropSafe",
        "total_workers": worker_count,
        "database": "connected" if worker_count >= 0 else "error",
    }
