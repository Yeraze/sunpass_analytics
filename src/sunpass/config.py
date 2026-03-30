import os
from pathlib import Path

DATA_DIR = Path(os.getenv("SUNPASS_DATA_DIR", "/app/data"))
DB_PATH = DATA_DIR / "sunpass.db"

SUNPASS_USERNAME = os.getenv("SUNPASS_USERNAME", "")
SUNPASS_PASSWORD = os.getenv("SUNPASS_PASSWORD", "")

SCRAPE_SCHEDULE = os.getenv("SUNPASS_SCRAPE_SCHEDULE", "0 6 * * *")
INITIAL_LOOKBACK_DAYS = int(os.getenv("SUNPASS_LOOKBACK_DAYS", "90"))

BASE_URL = "https://www.sunpass.com"
LOGIN_URL = f"{BASE_URL}/vector/account/login.do"
VEHICLES_URL = f"{BASE_URL}/vector/account/transponders/tagsandvehiclesList.do"
TRANSACTIONS_URL = f"{BASE_URL}/vector/account/transactions/webtransactionSearch.do"
