import asyncio

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates

from sunpass.config import SCRAPE_SCHEDULE
from sunpass.db.queries import get_dashboard_summary, get_scrape_logs, get_transaction_count
from sunpass.scraper.run import is_scraping, run_scrape

router = APIRouter()
templates = Jinja2Templates(directory="src/sunpass/templates")


@router.get("/settings", response_class=HTMLResponse)
async def settings_page(request: Request):
    logs = await get_scrape_logs()
    summary = await get_dashboard_summary()
    txn_count = await get_transaction_count()
    return templates.TemplateResponse(
        "settings.html",
        {
            "request": request,
            "logs": logs,
            "schedule": SCRAPE_SCHEDULE,
            "stats": {
                "vehicle_count": summary["vehicle_count"],
                "transponder_count": summary["transponder_count"],
                "transaction_count": txn_count,
            },
            "active_page": "settings",
        },
    )


@router.post("/api/scrape")
async def trigger_scrape():
    if is_scraping():
        return HTMLResponse('<span class="text-warning">Scrape already in progress...</span>')

    asyncio.create_task(run_scrape())
    return HTMLResponse('<span class="text-success">Scrape started!</span>')


@router.get("/api/scrape-status")
async def scrape_status():
    summary = await get_dashboard_summary()
    scraping = is_scraping()
    if scraping:
        return HTMLResponse('<span class="scrape-status-badge running">Scraping...</span>')
    elif summary["last_scrape"] and summary["last_scrape"]["status"] == "failed":
        return HTMLResponse('<span class="scrape-status-badge error">Last scrape failed</span>')
    else:
        return HTMLResponse('<span class="scrape-status-badge idle">Idle</span>')
