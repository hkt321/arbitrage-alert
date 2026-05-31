from pathlib import Path
from typing import Any

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.services.opportunity_service import OpportunityService


BACKEND_ROOT = Path(__file__).resolve().parents[2]
PROJECT_ROOT = BACKEND_ROOT.parent
WEB_ROOT = PROJECT_ROOT / "web"
service = OpportunityService(BACKEND_ROOT)

app = FastAPI(title="Arbitrage Alert API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/")
def index() -> FileResponse:
    return FileResponse(WEB_ROOT / "index.html")


@app.get("/api/opportunities")
def opportunities() -> dict[str, Any]:
    return {
        "data": service.score_watchlist(__file__),
    }


@app.get("/api/valuation-signals")
def valuation_signals() -> dict[str, Any]:
    return {
        "data": service.fetch_valuation_signals(__file__),
    }


app.mount("/src", StaticFiles(directory=WEB_ROOT / "src"), name="src")
