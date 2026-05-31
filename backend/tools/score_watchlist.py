import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
BACKEND = ROOT / "backend"
sys.path.insert(0, str(BACKEND))

from app.services.opportunity_service import OpportunityService


def main() -> None:
    results = OpportunityService(BACKEND).score_watchlist(__file__)
    print(json.dumps(results, ensure_ascii=False, indent=2, default=str))


if __name__ == "__main__":
    main()
