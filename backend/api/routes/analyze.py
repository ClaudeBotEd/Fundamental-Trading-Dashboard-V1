import logging
from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel
from core.models import BiasResult, Horizon
from api.cache import ResultCache

logger = logging.getLogger(__name__)
router = APIRouter()


def _get_cache(request: Request) -> ResultCache:
    return request.app.state.cache


def _get_analyzer(request: Request):
    return request.app.state.analyzer


class FeedbackPayload(BaseModel):
    feedback: str
    note: str | None = None


@router.get("/analyze/{pair:path}", response_model=BiasResult)
async def analyze_pair(
    pair: str,
    request: Request,
    horizon: Horizon = Horizon.WEEKLY,
    refresh: bool = False,
    cache: ResultCache = Depends(_get_cache),
    analyzer=Depends(_get_analyzer),
) -> BiasResult:
    pair = pair.replace("-", "/").upper()
    cached = cache.get(pair, horizon.value)
    if cached and not refresh:
        return cached
    try:
        result = await analyzer.analyze_pair(pair, horizon)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    cache.set(result)
    try:
        request.app.state.vault_writer.write_bias(result)
    except Exception as exc:
        logger.warning("Vault write failed: %s", exc)
    return result


@router.get("/analyze", response_model=list[BiasResult])
def list_cached(cache: ResultCache = Depends(_get_cache)) -> list[BiasResult]:
    return cache.all()


@router.post("/analyze/{pair:path}/feedback", status_code=204)
async def post_feedback(
    pair: str,
    payload: FeedbackPayload,
    request: Request,
    cache: ResultCache = Depends(_get_cache),
) -> None:
    pair = pair.replace("-", "/").upper()
    cached = cache.get(pair, Horizon.WEEKLY.value)
    if cached is None:
        raise HTTPException(status_code=404, detail="No cached result for this pair")
    vault_writer = request.app.state.vault_writer
    date_str = cached.timestamp.strftime("%Y-%m-%d")
    try:
        vault_writer.update_bias_feedback(
            pair=pair,
            horizon=Horizon.WEEKLY.value,
            date_str=date_str,
            feedback=payload.feedback,
            note=payload.note,
        )
    except (FileNotFoundError, ValueError) as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
