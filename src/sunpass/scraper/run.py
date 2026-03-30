import logging

from sunpass.db.queries import create_scrape_log, get_scrape_logs, update_scrape_log
from sunpass.scraper.auth import create_browser_context, login
from sunpass.scraper.transactions import scrape_transactions
from sunpass.scraper.vehicles import scrape_vehicles_and_transponders

logger = logging.getLogger(__name__)

# Module-level flag to prevent concurrent scrapes
_scraping = False


def is_scraping() -> bool:
    return _scraping


async def run_scrape(from_date: str | None = None):
    """Run a full scrape cycle: login, scrape vehicles, scrape transactions."""
    global _scraping
    if _scraping:
        logger.warning("Scrape already in progress, skipping")
        return

    _scraping = True
    log_id = await create_scrape_log()
    pw = None
    browser = None

    try:
        pw, browser, context = await create_browser_context()
        page = await login(context)

        vehicles_added, transponders_added = await scrape_vehicles_and_transponders(page)

        # Determine start date for transactions
        if not from_date:
            logs = await get_scrape_logs(limit=2)
            # Use the last successful scrape date if available
            for log in logs:
                if log["status"] == "success" and log["id"] != log_id:
                    from_date = log["started_at"][:10]
                    break

        transactions_added = await scrape_transactions(page, from_date)

        await update_scrape_log(
            log_id,
            status="success",
            transactions_added=transactions_added,
            vehicles_added=vehicles_added,
            transponders_added=transponders_added,
        )
        logger.info(
            "Scrape complete: %d vehicles, %d transponders, %d transactions",
            vehicles_added,
            transponders_added,
            transactions_added,
        )

    except Exception as e:
        logger.error("Scrape failed: %s", e)
        await update_scrape_log(log_id, status="failed", error_message=str(e))
        raise

    finally:
        if browser:
            await browser.close()
        if pw:
            await pw.stop()
        _scraping = False
