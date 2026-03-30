import logging

from playwright.async_api import Page

from sunpass.config import VEHICLES_URL
from sunpass.db.queries import upsert_transponder, upsert_vehicle
from sunpass.scraper.auth import take_screenshot

logger = logging.getLogger(__name__)


async def scrape_vehicles_and_transponders(page: Page) -> tuple[int, int]:
    """Scrape vehicles and transponders page. Returns (vehicles_added, transponders_added)."""
    vehicles_added = 0
    transponders_added = 0

    logger.info("Navigating to vehicles/transponders page")
    await page.goto(VEHICLES_URL, wait_until="networkidle", timeout=30000)
    await page.wait_for_timeout(3000)
    await take_screenshot(page, "vehicles_page")

    # SunPass footable columns:
    # 0: Transponder Number
    # 1: Transponder Type
    # 2: Transponder Status
    # 3: Associated Plate
    # 4: Friendly Name
    # 5: Choose an Action (skip)
    rows = await page.query_selector_all("table tbody tr")
    logger.info("Found %d vehicle/transponder rows", len(rows))

    for row in rows:
        try:
            cells = await row.query_selector_all("td")
            if not cells or len(cells) < 5:
                continue

            transponder_id = (await cells[0].text_content() or "").strip()
            transponder_type = (await cells[1].text_content() or "").strip()
            status = (await cells[2].text_content() or "").strip()
            plate_text = (await cells[3].text_content() or "").strip()
            friendly_name = (await cells[4].text_content() or "").strip()

            if not transponder_id or not transponder_id[0].isdigit():
                continue

            logger.info(
                "Transponder: %s | Type: %s | Status: %s | Plate: %s | Name: %s",
                transponder_id, transponder_type, status, plate_text, friendly_name,
            )

            # Use transponder_id as vehicle_id since SunPass links them 1:1
            vehicle_id = transponder_id

            # Parse plate and state if present (format: "PLATE" or could include state)
            license_plate = plate_text if plate_text else None
            license_state = None

            added = await upsert_vehicle(
                vehicle_id=vehicle_id,
                license_plate=license_plate,
                license_state=license_state,
            )
            if added:
                vehicles_added += 1

            added = await upsert_transponder(
                transponder_id=transponder_id,
                transponder_type=transponder_type or None,
                status=status or None,
                vehicle_id=vehicle_id,
            )
            if added:
                transponders_added += 1

        except Exception as e:
            logger.error("Error parsing vehicle row: %s", e)
            continue

    logger.info(
        "Vehicles scraped: %d new/updated, Transponders: %d new/updated",
        vehicles_added, transponders_added,
    )
    return vehicles_added, transponders_added
