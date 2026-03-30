# SunPass Data Scraper & Dashboard — Design Spec

## Context

SunPass (sunpass.com) is Florida's toll transponder system. The user wants to scrape their account data (vehicles, transponders, transactions) and visualize it locally for exploration by road, vehicle, transponder, and date range. SunPass has no public API — data must be extracted via browser automation against a legacy Java/Struts web application protected by Imperva WAF.

## Architecture Overview

Single Docker container running a Python application with three responsibilities:

1. **Scraper** — Playwright headless browser logs into SunPass and extracts data
2. **Data Store** — SQLite database persisted via Docker volume
3. **Dashboard** — FastAPI web server with HTMX interactive UI and Chart.js graphs

```
┌─────────────────────────────────────┐
│         Docker Container            │
│                                     │
│  ┌───────────┐    ┌──────────────┐  │
│  │  Scraper   │───▶│   SQLite DB  │  │
│  │ (Playwright)│   │  (volume)    │  │
│  └───────────┘    └──────┬───────┘  │
│                          │          │
│  ┌───────────────────────┴───────┐  │
│  │     FastAPI Dashboard         │  │
│  │  (Jinja2 + HTMX + Chart.js)  │  │
│  └───────────────────────────────┘  │
│                                     │
│  ┌───────────────────────────────┐  │
│  │  APScheduler (cron triggers)  │  │
│  └───────────────────────────────┘  │
└─────────────────────────────────────┘
```

## Technology Stack

| Component | Technology | Rationale |
|-----------|-----------|-----------|
| Scraping | Playwright (Python, async) | Handles WAF, JS rendering, cookies natively; lighter than Selenium |
| Backend | FastAPI | Async, lightweight, great for serving templates and API endpoints |
| Templates | Jinja2 | Server-rendered HTML, no build step |
| Interactivity | HTMX | Dynamic filtering/loading without a JS framework |
| Tables | DataTables.js | Sortable, searchable, paginated tables out of the box |
| Charts | Chart.js | Simple, well-documented charting library |
| Database | SQLite (aiosqlite) | Zero config, file-based, perfect for single-user local app |
| Scheduling | APScheduler | In-process cron scheduler, status visible from dashboard |
| Container | Docker + docker compose | Single container, env vars for config |
| Python deps | uv | Fast dependency management |

## Data Model

### Tables

**vehicles**
```sql
CREATE TABLE vehicles (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    vehicle_id TEXT UNIQUE NOT NULL,     -- SunPass internal ID
    make TEXT,
    model TEXT,
    year TEXT,
    color TEXT,
    license_plate TEXT,
    license_state TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

**transponders**
```sql
CREATE TABLE transponders (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    transponder_id TEXT UNIQUE NOT NULL,  -- SunPass transponder number
    transponder_type TEXT,                -- e.g., mini, portable
    status TEXT,                          -- active, inactive
    vehicle_id TEXT,                      -- FK to vehicles.vehicle_id
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (vehicle_id) REFERENCES vehicles(vehicle_id)
);
```

**transactions**
```sql
CREATE TABLE transactions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    transaction_id TEXT UNIQUE,           -- SunPass transaction reference if available
    transaction_date TIMESTAMP NOT NULL,
    posted_date TIMESTAMP,
    transponder_id TEXT,
    vehicle_id TEXT,
    plaza_name TEXT,                      -- toll plaza / road name
    agency TEXT,                          -- e.g., CFX, FDOT, MDX
    amount REAL NOT NULL,
    transaction_type TEXT,                -- toll, replenishment, fee, etc.
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (transponder_id) REFERENCES transponders(transponder_id),
    FOREIGN KEY (vehicle_id) REFERENCES vehicles(vehicle_id)
);
```

**scrape_log**
```sql
CREATE TABLE scrape_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    started_at TIMESTAMP NOT NULL,
    completed_at TIMESTAMP,
    status TEXT NOT NULL,                 -- running, success, failed
    error_message TEXT,
    transactions_added INTEGER DEFAULT 0,
    vehicles_added INTEGER DEFAULT 0,
    transponders_added INTEGER DEFAULT 0
);
```

### Indexes
- `transactions(transaction_date)` — date range queries
- `transactions(plaza_name)` — filter by road
- `transactions(vehicle_id)` — filter by vehicle
- `transactions(transponder_id)` — filter by transponder

## Scraper Design

### Login Flow
1. Launch Playwright Chromium browser (headless)
2. Navigate to `https://www.sunpass.com/vector/account/login.do`
3. Fill `loginName` and `password` fields
4. Submit form and wait for navigation to account dashboard
5. Detect login success (check for account page elements) or failure (error message)
6. Handle potential 2FA or CAPTCHA by logging error and notifying via dashboard

### Transponders & Vehicles Scrape
1. Navigate to `/vector/account/transponders/tagsandvehiclesList.do`
2. Wait for page load and any AJAX content
3. Parse the HTML table(s) for vehicle and transponder data
4. Upsert into `vehicles` and `transponders` tables (update on conflict)

### Transaction Scrape
1. Navigate to `/vector/account/transactions/webtransactionSearch.do`
2. Set date range filter: from last scrape date (or 90 days ago on first run) to today
3. Submit search form
4. Parse transaction table rows
5. Handle pagination — iterate through all pages
6. Insert new transactions (skip duplicates via UNIQUE constraint)
7. Update `scrape_log` with results

### Error Handling
- Retry login up to 3 times with exponential backoff
- Screenshot on failure (saved to volume for debugging)
- Log all scrape attempts to `scrape_log` table
- Dashboard shows scrape status and last error

## Dashboard Design

### Pages

**Dashboard Home (`/`)**
- Summary cards: total tolls this month, total tolls this year, number of vehicles, last scrape time
- Spending trend chart (line chart, last 12 months)
- Quick action: "Scrape Now" button
- Scrape status indicator (idle / running / last error)

**Transactions (`/transactions`)**
- DataTable with all transactions (sortable, searchable, paginated)
- Filter bar (HTMX-powered, no page reload):
  - Date range picker
  - Vehicle dropdown
  - Transponder dropdown
  - Road/plaza dropdown
- Export to CSV button

**Analytics (`/analytics`)**
- **By Road**: Bar chart of total spending per plaza/road
- **By Vehicle**: Pie chart of spending per vehicle
- **By Transponder**: Spending breakdown per transponder
- **By Date**: Line chart with configurable date range
- **By Day of Week**: Bar chart showing toll patterns
- All charts are interactive (Chart.js) and filterable by date range

**Vehicles & Transponders (`/vehicles`)**
- Table listing all vehicles with their assigned transponders
- Status indicators for transponder status

**Settings (`/settings`)**
- Scrape schedule configuration (cron expression or simple interval)
- View scrape history/log
- Manual scrape trigger with live status

### HTMX Interaction Pattern
- Filter changes trigger `hx-get` to FastAPI endpoints returning HTML fragments
- Chart data loaded via JSON API endpoints, rendered by Chart.js
- Scrape trigger via `hx-post` with progress polling via `hx-trigger="every 2s"`

## Project Structure

```
sunpass/
├── docker-compose.yml
├── Dockerfile
├── pyproject.toml
├── src/
│   └── sunpass/
│       ├── __init__.py
│       ├── main.py              # FastAPI app + APScheduler setup
│       ├── config.py            # Settings from env vars
│       ├── db/
│       │   ├── __init__.py
│       │   ├── models.py        # SQLite schema + migrations
│       │   └── queries.py       # Data access functions
│       ├── scraper/
│       │   ├── __init__.py
│       │   ├── auth.py          # Login flow
│       │   ├── vehicles.py      # Vehicles & transponders scrape
│       │   └── transactions.py  # Transaction scrape
│       ├── routes/
│       │   ├── __init__.py
│       │   ├── dashboard.py     # Home page
│       │   ├── transactions.py  # Transaction views + API
│       │   ├── analytics.py     # Charts + data API
│       │   ├── vehicles.py      # Vehicles & transponders view
│       │   └── settings.py      # Settings + scrape control
│       ├── templates/
│       │   ├── base.html        # Base layout with nav
│       │   ├── dashboard.html
│       │   ├── transactions.html
│       │   ├── analytics.html
│       │   ├── vehicles.html
│       │   ├── settings.html
│       │   └── fragments/       # HTMX partial templates
│       │       ├── transaction_table.html
│       │       ├── chart_data.html
│       │       └── scrape_status.html
│       └── static/
│           ├── css/
│           │   └── style.css
│           └── js/
│               └── charts.js    # Chart.js initialization
├── data/                        # Docker volume mount point
│   └── sunpass.db
└── tests/
    ├── test_scraper.py
    ├── test_queries.py
    └── test_routes.py
```

## Docker Configuration

### docker-compose.yml
- Single service: `sunpass`
- Environment variables: `SUNPASS_USERNAME`, `SUNPASS_PASSWORD`, `SCRAPE_SCHEDULE` (default: `0 6 * * *` — daily at 6 AM)
- Volume: `./data:/app/data` for SQLite persistence
- Port: `8080:8080`
- Restart policy: `unless-stopped`

### Dockerfile
- Base: `python:3.12-slim`
- Install Playwright + Chromium dependencies
- Install Python deps via uv
- Run via uvicorn

## Verification Plan

1. **Build and start**: `docker compose up --build` — container starts without errors
2. **Login test**: Trigger manual scrape from dashboard, verify login succeeds (check scrape_log)
3. **Data scrape**: Verify vehicles, transponders, and transactions appear in respective tables
4. **Dashboard**: Navigate all pages, verify tables render with data
5. **Filters**: Test date range, vehicle, and road filters on transactions page
6. **Charts**: Verify all analytics charts render with correct data
7. **Scheduling**: Verify APScheduler triggers scrape at configured time (check scrape_log)
8. **Persistence**: Restart container, verify data survives (`docker compose down && docker compose up`)
9. **Error handling**: Test with bad credentials, verify error appears in dashboard
