import logging
from contextlib import asynccontextmanager
from pathlib import Path

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from sunpass.config import SCRAPE_SCHEDULE
from sunpass.db.models import init_db
from sunpass.routes import analytics, dashboard, map, settings, transactions, vehicles
from sunpass.scraper.run import run_scrape

PACKAGE_DIR = Path(__file__).resolve().parent

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

scheduler = AsyncIOScheduler()


def parse_cron_schedule(expr: str) -> dict:
    """Parse a cron expression (minute hour day month day_of_week) into CronTrigger kwargs."""
    parts = expr.strip().split()
    if len(parts) != 5:
        logger.warning("Invalid cron expression '%s', using default (daily 6am)", expr)
        return {"hour": 6, "minute": 0}
    return {
        "minute": parts[0],
        "hour": parts[1],
        "day": parts[2],
        "month": parts[3],
        "day_of_week": parts[4],
    }


async def scheduled_scrape():
    try:
        await run_scrape()
    except Exception as e:
        logger.error("Scheduled scrape failed: %s", e)


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    logger.info("Database initialized")

    cron_kwargs = parse_cron_schedule(SCRAPE_SCHEDULE)
    scheduler.add_job(scheduled_scrape, CronTrigger(**cron_kwargs), id="sunpass_scrape")
    scheduler.start()
    logger.info("Scheduler started with schedule: %s", SCRAPE_SCHEDULE)

    yield

    scheduler.shutdown()
    logger.info("Scheduler stopped")


app = FastAPI(title="SunPass Dashboard", lifespan=lifespan)

app.mount("/static", StaticFiles(directory=str(PACKAGE_DIR / "static")), name="static")

app.include_router(dashboard.router)
app.include_router(transactions.router)
app.include_router(analytics.router)
app.include_router(map.router)
app.include_router(vehicles.router)
app.include_router(settings.router)
