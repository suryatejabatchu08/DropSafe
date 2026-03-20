from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from routers.premium import router as premium_router
from routers.triggers import router as triggers_router
from routers.fraud import router as fraud_router

app = FastAPI(title="DropSafe", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[],
    allow_origin_regex=r"^http://localhost:\d+$",
    # Vite sometimes picks a different localhost port; allow any dev port.
    # (Regex support keeps Phase 1 simple without hardcoding ports.)
    # Note: `allow_origin_regex` doesn’t support wildcard strings.
    allow_headers=["*"],
    allow_methods=["*"],
    allow_credentials=False,
)

app.include_router(premium_router)
app.include_router(triggers_router)
app.include_router(fraud_router)


@app.get("/health")
async def health():
    return {"status": "ok", "project": "DropSafe"}

