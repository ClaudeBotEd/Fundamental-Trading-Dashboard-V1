from fastapi import APIRouter

SUPPORTED_PAIRS = [
    "XAU/USD",
    "EUR/USD",
    "GBP/USD",
    "USD/JPY",
    "AUD/USD",
    "USD/CAD",
    "USD/CHF",
    "NZD/USD",
    "BTC/USD",
    "ETH/USD",
]

router = APIRouter()


@router.get("/pairs")
def get_pairs() -> list[str]:
    return SUPPORTED_PAIRS
