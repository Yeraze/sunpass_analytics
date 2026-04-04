import asyncio
import logging
from pathlib import Path

from playwright.async_api import Browser, BrowserContext, Page, Playwright, async_playwright

from sunpass.config import BASE_URL, LOGIN_URL, SUNPASS_PASSWORD, SUNPASS_USERNAME

logger = logging.getLogger(__name__)

SCREENSHOT_DIR = Path("/app/data/screenshots")


async def take_screenshot(page: Page, name: str) -> None:
    SCREENSHOT_DIR.mkdir(parents=True, exist_ok=True)
    path = SCREENSHOT_DIR / f"{name}.png"
    await page.screenshot(path=str(path))
    logger.info("Screenshot saved: %s", path)


async def login(context: BrowserContext, max_retries: int = 3) -> Page:
    """Login to SunPass and return the authenticated page."""
    page = await context.new_page()

    for attempt in range(1, max_retries + 1):
        try:
            logger.info("Login attempt %d/%d", attempt, max_retries)
            await page.goto(BASE_URL, wait_until="networkidle", timeout=60000)
            await page.wait_for_timeout(3000)

            # Click "MY SUNPASS" to reveal the login form
            my_sunpass = await page.query_selector(
                'a:has-text("MY SUNPASS"), a:has-text("My SunPass")'
            )
            if my_sunpass:
                await my_sunpass.click()
                await page.wait_for_timeout(2000)
            else:
                logger.warning("MY SUNPASS button not found, trying direct login")
                await page.goto(LOGIN_URL, wait_until="networkidle", timeout=30000)

            await page.fill('input[name="loginName"]', SUNPASS_USERNAME)
            await page.fill('input[name="password"]', SUNPASS_PASSWORD)

            # Find and click the login submit button
            submit_btn = await page.query_selector(
                '#tt_submit, button[type="submit"], input[type="submit"]'
            )
            if submit_btn:
                await submit_btn.click()
            else:
                await page.click('button[type="submit"], input[type="submit"]')

            await page.wait_for_load_state("networkidle", timeout=30000)

            # Check for login failure indicators
            error_el = await page.query_selector(".error-message, .alert-danger, .errorMessage")
            if error_el:
                error_text = await error_el.text_content()
                raise RuntimeError(f"Login failed: {error_text}")

            # Verify we're on an authenticated page
            if "/account/" in page.url or "dashboard" in page.url.lower():
                logger.info("Login successful, landed on: %s", page.url)
                return page

            # If URL didn't change as expected, check page content
            await take_screenshot(page, f"login_attempt_{attempt}")
            raise RuntimeError(f"Unexpected page after login: {page.url}")

        except Exception as e:
            logger.error("Login attempt %d failed: %s", attempt, e)
            await take_screenshot(page, f"login_error_{attempt}")
            if attempt == max_retries:
                raise
            await asyncio.sleep(2**attempt)

    raise RuntimeError("Login failed after all retries")


async def create_browser_context() -> tuple[Playwright, Browser, BrowserContext]:
    """Create and return (playwright, browser, context) tuple."""
    pw = await async_playwright().start()
    browser = await pw.chromium.launch(headless=True)
    context = await browser.new_context(
        viewport={"width": 1280, "height": 720},
        user_agent=(
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/120.0.0.0 Safari/537.36"
        ),
    )
    return pw, browser, context
