"""GET /market — live top-bar metrics (DXY, US10Y, VIX, real yield)."""

from fastapi import APIRouter, Request
from fetchers.market_data import MarketDataFetcher, MarketSnapshot

router = APIRouter()

# Label → key mapping for display order
_DISPLAY = [
    ("DXY", "dxy"),
    ("US10Y", "us10y"),
    ("VIX", "vix"),
]


def _snapshot_to_legacy(label: str, snap: MarketSnapshot) -> dict:
    """Convert a MarketSnapshot to the array-item format the frontend expects."""
    if snap.value is None:
        return {"label": label, "value": None, "change": None, "changePct": None}

    if label == "US10Y":
        # Frontend displays yields as "4.52%"; changePct in bps
        return {
            "label": label,
            "value": round(snap.value, 2),
            "change": round(snap.change, 2) if snap.change is not None else None,
            "changePct": round(snap.change_pct, 2) if snap.change_pct is not None else None,
        }

    return {
        "label": label,
        "value": round(snap.value, 2),
        "change": round(snap.change, 2) if snap.change is not None else None,
        "changePct": round(snap.change_pct, 2) if snap.change_pct is not None else None,
    }


@router.get("/market")
async def market_metrics(request: Request):
    fetcher: MarketDataFetcher = request.app.state.market_fetcher
    snapshots = await fetcher.fetch_all()

    # Store latest snapshots on app.state so the analyzer can read them
    request.app.state.market_snapshots = snapshots

    # Return the array format the frontend top-bar expects
    return [_snapshot_to_legacy(label, snapshots[key]) for label, key in _DISPLAY]
