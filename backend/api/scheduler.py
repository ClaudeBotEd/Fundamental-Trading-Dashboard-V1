import logging
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from core.models import Horizon
from api.routes.pairs import SUPPORTED_PAIRS

logger = logging.getLogger(__name__)


def build_scheduler(analyzer, cache) -> AsyncIOScheduler:
    scheduler = AsyncIOScheduler()

    async def _refresh_all() -> None:
        logger.info("Scheduler: refreshing all pairs")
        for pair in SUPPORTED_PAIRS:
            try:
                result = await analyzer.analyze_pair(pair, Horizon.WEEKLY)
                cache.set(result)
                logger.info("Refreshed %s → %s (%s%%)", pair, result.bias.value, result.conviction)
            except Exception as exc:
                logger.error("Failed to refresh %s: %s", pair, exc)

    scheduler.add_job(_refresh_all, "interval", hours=4, id="refresh_all")
    return scheduler
