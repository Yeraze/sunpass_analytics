import logging
import re
from datetime import datetime, timedelta

from playwright.async_api import Page

from sunpass.config import INITIAL_LOOKBACK_DAYS, TRANSACTIONS_URL
from sunpass.db.queries import get_vehicles, insert_transaction
from sunpass.scraper.auth import take_screenshot

logger = logging.getLogger(__name__)


async def scrape_transactions(page: Page, from_date: str | None = None) -> int:
    """Scrape transactions. Returns count of new transactions added.

    Args:
        page: Authenticated Playwright page
        from_date: Start date as YYYY-MM-DD. Defaults to INITIAL_LOOKBACK_DAYS ago.
    """
    if not from_date:
        start = datetime.now() - timedelta(days=INITIAL_LOOKBACK_DAYS)
        from_date_mm = start.strftime("%m/%d/%Y")
    elif "-" in from_date:
        dt = datetime.strptime(from_date, "%Y-%m-%d")
        from_date_mm = dt.strftime("%m/%d/%Y")
    else:
        from_date_mm = from_date

    to_date_mm = datetime.now().strftime("%m/%d/%Y")

    logger.info("Scraping transactions from %s to %s", from_date_mm, to_date_mm)

    await page.goto(TRANSACTIONS_URL, wait_until="networkidle", timeout=30000)
    await page.wait_for_timeout(3000)

    # Fill date range — SunPass uses startDateAll / endDateAll fields
    start_input = await page.query_selector('#startDateAll1, input[name="startDateAll"]')
    end_input = await page.query_selector('#endDateAll1, input[name="endDateAll"]')

    if start_input:
        await start_input.fill("")
        await start_input.fill(from_date_mm)
        logger.info("Set start date: %s", from_date_mm)
    if end_input:
        await end_input.fill("")
        await end_input.fill(to_date_mm)
        logger.info("Set end date: %s", to_date_mm)

    # Click the VIEW button to search
    view_btn = await page.query_selector(
        'input[name="btnView"], button:has-text("VIEW"), button:has-text("View")'
    )
    if view_btn:
        await view_btn.click()
        await page.wait_for_load_state("networkidle", timeout=60000)
        await page.wait_for_timeout(3000)
    else:
        logger.warning("VIEW button not found")

    await take_screenshot(page, "transactions_page")

    total_added = 0
    page_num = 1

    while True:
        logger.info("Parsing transaction page %d", page_num)
        added = await _parse_transaction_page(page)
        total_added += added

        # Check for next page
        next_btn = await page.query_selector(
            'a.next, .pagination .next a, a[aria-label="Next"], .nextPage, a:has-text("Next")'
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

    logger.info("Total new transactions added: %d", total_added)
    return total_added


async def _parse_transaction_page(page: Page) -> int:
    """Parse transactions from current page.

    SunPass footable columns:
    0: Posted Date (MM/DD/YYYY)
    1: Transaction Date (MM/DD/YYYY)
    2: Transaction Details (hidden, contains rich data)
    3: Transaction Time (HH:MM:SS AM/PM)
    4: Transponder/License Plate (e.g. "LNWG73-FL" or transponder number)
    5: Description (plaza/road name)
    6: Debit (-) amount
    7: Credit (+) amount
    8: Balance
    """
    added = 0

    rows = await page.query_selector_all("table tbody tr")
    logger.info("Found %d transaction rows", len(rows))

    for row in rows:
        try:
            cells = await row.query_selector_all("td")
            if not cells or len(cells) < 7:
                continue

            posted_date_str = (await cells[0].text_content() or "").strip()
            txn_date_str = (await cells[1].text_content() or "").strip()
            details_html = await cells[2].inner_html() if len(cells) > 2 else ""
            txn_time_str = (await cells[3].text_content() or "").strip()
            plate_transponder = (await cells[4].text_content() or "").strip()
            description = (await cells[5].text_content() or "").strip()
            debit_str = (await cells[6].text_content() or "").strip()
            credit_str = (await cells[7].text_content() or "").strip() if len(cells) > 7 else ""

            # Skip non-data rows
            if not posted_date_str or not posted_date_str[0].isdigit():
                continue

            # Parse dates
            posted_date = _parse_date(posted_date_str)
            txn_date = _parse_date(txn_date_str)

            # Combine transaction date with time in ISO format
            if txn_date and txn_time_str:
                txn_datetime = _combine_date_time(txn_date, txn_time_str)
            elif txn_date:
                txn_datetime = txn_date
            else:
                continue

            # Parse amount (debit is expense, credit is income)
            amount = _parse_amount(debit_str)
            if amount is None:
                amount = _parse_amount(credit_str)
                if amount is not None:
                    amount = -amount  # Credits are negative (refunds/replenishments)
            if amount is None:
                amount = 0.0

            # Parse details for extra info
            details = _parse_details(details_html)

            # Parse transponder/plate field: "LNWG73-FL" or "036939281010"
            transponder_id = None
            license_plate = None
            plate_text = plate_transponder.split("\n")[0].strip()  # Remove "(view image)" link text
            plate_text = re.sub(r'\(view image\)', '', plate_text).strip()

            if plate_text.replace("-", "").replace(" ", "").isdigit() and len(plate_text) >= 8:
                transponder_id = plate_text
            elif "-" in plate_text:
                # Format: PLATE-STATE (e.g. LNWG73-FL)
                parts = plate_text.rsplit("-", 1)
                license_plate = parts[0]
            elif plate_text:
                license_plate = plate_text

            # Look up vehicle_id by plate if no transponder
            vehicle_id = transponder_id
            if not vehicle_id and license_plate:
                vehicles = await get_vehicles()
                for v in vehicles:
                    if v.get("license_plate") == license_plate:
                        vehicle_id = v["vehicle_id"]
                        break

            # Determine transaction type
            txn_type = details.get("transaction_type", "Toll" if amount > 0 else "Credit")

            # Generate unique transaction ID
            txn_id = details.get("transaction_number")
            if not txn_id:
                txn_id = f"{txn_datetime}_{plate_text}_{description}_{amount}"

            logger.debug(
                "Transaction: %s | %s | %s | %s | $%.2f",
                txn_datetime, plate_text, description, txn_type, amount,
            )

            inserted = await insert_transaction(
                transaction_id=txn_id,
                transaction_date=txn_datetime,
                posted_date=posted_date,
                transponder_id=transponder_id,
                vehicle_id=vehicle_id,
                plaza_name=description or details.get("location"),
                agency=details.get("agency"),
                amount=amount,
                transaction_type=txn_type,
            )
            if inserted:
                added += 1

        except Exception as e:
            logger.error("Error parsing transaction row: %s", e)
            continue

    return added


def _parse_date(date_str: str) -> str | None:
    """Parse MM/DD/YYYY to YYYY-MM-DD."""
    date_str = date_str.strip()
    if not date_str:
        return None
    try:
        if len(date_str.split("/")[2]) == 2:
            dt = datetime.strptime(date_str, "%m/%d/%y")
        else:
            dt = datetime.strptime(date_str, "%m/%d/%Y")
        return dt.strftime("%Y-%m-%d")
    except (ValueError, IndexError):
        return None


def _combine_date_time(date_iso: str, time_str: str) -> str:
    """Combine YYYY-MM-DD date with '05:59:57 PM' time into ISO datetime."""
    time_str = time_str.strip()
    try:
        if "AM" in time_str.upper() or "PM" in time_str.upper():
            t = datetime.strptime(time_str, "%I:%M:%S %p")
        else:
            t = datetime.strptime(time_str, "%H:%M:%S")
        return f"{date_iso} {t.strftime('%H:%M:%S')}"
    except ValueError:
        return f"{date_iso} {time_str}"


def _parse_amount(amount_str: str) -> float | None:
    """Parse $X.XX to float."""
    amount_str = amount_str.strip()
    if not amount_str:
        return None
    cleaned = amount_str.replace("$", "").replace(",", "").strip()
    if not cleaned:
        return None
    try:
        return float(cleaned)
    except ValueError:
        return None


def _parse_details(html: str) -> dict:
    """Parse the hidden transaction details HTML for extra fields."""
    result = {}

    patterns = {
        "transaction_number": r"Transaction Number:\s*</b>\s*(\S+)",
        "agency": r"Agency Name:\s*</b>\s*([^<]+)",
        "location": r"Location:\s*</b>\s*([^<]+)",
        "lane": r"Lane:\s*</b>\s*(\S+)",
        "axle": r"Axle:\s*</b>\s*(\d+)",
        "transaction_type": r"Transaction Type:\s*</b>\s*([^<]+)",
    }

    for key, pattern in patterns.items():
        match = re.search(pattern, html, re.IGNORECASE)
        if match:
            result[key] = match.group(1).strip()

    return result
