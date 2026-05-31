from pathlib import Path
from threading import Lock
from time import monotonic
from typing import Any

from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.services.opportunity_service import OpportunityService


BACKEND_ROOT = Path(__file__).resolve().parents[2]
PROJECT_ROOT = BACKEND_ROOT.parent
WEB_ROOT = PROJECT_ROOT / "web"
service = OpportunityService(BACKEND_ROOT)
OPPORTUNITY_CACHE_TTL_SECONDS = 45


class ApiCache:
    def __init__(self, ttl_seconds: int) -> None:
        self.ttl_seconds = ttl_seconds
        self._lock = Lock()
        self._data: list[dict[str, Any]] | None = None
        self._stored_at = 0.0
        self._as_of = ""

    def get(self, force_refresh: bool, loader: Any) -> dict[str, Any]:
        with self._lock:
            now = monotonic()
            is_fresh = self._data is not None and now - self._stored_at < self.ttl_seconds
            if force_refresh or not is_fresh:
                self._data = loader()
                self._stored_at = monotonic()
                self._as_of = self._iso_now()
                cached = False
            else:
                cached = True

            age_seconds = round(monotonic() - self._stored_at, 3)
            return {
                "data": self._data or [],
                "meta": {
                    "cached": cached,
                    "asOf": self._as_of,
                    "ageSeconds": age_seconds,
                    "ttlSeconds": self.ttl_seconds,
                },
            }

    @staticmethod
    def _iso_now() -> str:
        from datetime import datetime

        return datetime.now().isoformat(timespec="seconds")


opportunity_cache = ApiCache(OPPORTUNITY_CACHE_TTL_SECONDS)

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
def opportunities(refresh: bool = Query(False, description="Force refresh live data")) -> dict[str, Any]:
    return opportunity_cache.get(
        force_refresh=refresh,
        loader=lambda: service.score_watchlist(__file__),
    )


@app.get("/api/valuation-signals")
def valuation_signals() -> dict[str, Any]:
    return {
        "data": service.fetch_valuation_signals(__file__),
    }


app.mount("/src", StaticFiles(directory=WEB_ROOT / "src"), name="src")
