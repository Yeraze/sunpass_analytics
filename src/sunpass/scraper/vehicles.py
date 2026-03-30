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

    page_num = 1
    while True:
        logger.info("Parsing vehicles page %d", page_num)
        v_added, t_added = await _parse_vehicles_page(page)
        vehicles_added += v_added
        transponders_added += t_added

        # Check for next page link
        next_btn = await page.query_selector(
            'a.next, .pagination .next a, a[aria-label="Next"], '
            'a:has-text("Next"), a:has-text("next"), li.next a'
        )
        if next_btn:
            is_disabled = await next_btn.get_attribute("class") or ""
            if "disabled" in is_disabled:
                break
            await next_btn.click()
            await page.wait_for_load_state("networkidle", timeout=30000)
            await page.wait_for_timeout(2000)
            page_num += 1
        else:
            break

    logger.info(
        "Vehicles scraped: %d new/updated, Transponders: %d new/updated",
        vehicles_added, transponders_added,
    )
    return vehicles_added, transponders_added


async def _parse_vehicles_page(page: Page) -> tuple[int, int]:
    """Parse a single page of vehicles/transponders. Returns (vehicles_added, transponders_added)."""
    vehicles_added = 0
    transponders_added = 0

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

            vehicle_id = transponder_id
            license_plate = plate_text if plate_text else None

            added = await upsert_vehicle(
                vehicle_id=vehicle_id,
                friendly_name=friendly_name or None,
                license_plate=license_plate,
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

    return vehicles_added, transponders_added
