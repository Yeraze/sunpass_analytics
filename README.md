# SunPass Analytics

A Dockerized web application that scrapes your [SunPass](https://www.sunpass.com) toll account data and presents it in an interactive dashboard with charts, filters, and a heatmap.

## Features

- **Automated Scraping** — Playwright headless browser logs into SunPass and extracts vehicles, transponders, and transactions
- **Interactive Dashboard** — Summary cards, monthly spending trends, quick stats
- **Transaction Explorer** — Sortable/searchable table with filters by date, vehicle, road, and transponder. CSV export included
- **Analytics Charts** — Daily spending by vehicle (stacked, toggleable), spending by road/vehicle/transponder (pie charts with inline labels), monthly trends, day-of-week patterns
- **Toll Heatmap** — Leaflet.js map with heatmap overlay showing frequently used toll plazas. Click markers for trip counts and totals
- **Vehicles & Transponders** — View all linked devices with friendly names, plates, and statuses
- **Scheduled Scraping** — Configurable cron schedule (default: daily at 6 AM) with manual trigger from the dashboard
- **Stable Chart Colors** — Each vehicle and road keeps the same color regardless of date range filters

## Screenshots
<img width="1333" height="972" alt="Screenshot 2026-03-31 at 12 05 39 PM" src="https://github.com/user-attachments/assets/342a6be8-6ca7-4f29-9037-9043b7b32ae5" />

<img width="1332" height="957" alt="Screenshot 2026-03-31 at 12 05 53 PM" src="https://github.com/user-attachments/assets/fe6f035a-5d09-4078-95f1-921c33757447" />


## Quick Start

### Prerequisites

- [Docker](https://docs.docker.com/get-docker/) and Docker Compose

### 1. Clone the repository

```bash
git clone https://github.com/Yeraze/sunpass_analytics.git
cd sunpass_analytics
```

### 2. Configure credentials

Copy the example environment file and fill in your SunPass login details:

```bash
cp .env.example .env
```

Edit `.env`:

```
SUNPASS_USERNAME=your_sunpass_username
SUNPASS_PASSWORD=your_sunpass_password
SUNPASS_SCRAPE_SCHEDULE=0 6 * * *
```

| Variable | Description | Default |
|----------|-------------|---------|
| `SUNPASS_USERNAME` | Your SunPass account username or account number | *(required)* |
| `SUNPASS_PASSWORD` | Your SunPass account password | *(required)* |
| `SUNPASS_SCRAPE_SCHEDULE` | Cron expression for automatic scraping | `0 6 * * *` (daily at 6 AM UTC) |

### 3. Build and run

```bash
docker compose up -d --build
```

The dashboard will be available at **http://localhost:9180**.

### 4. Initial data load

The first scrape will run at the next scheduled time. To scrape immediately, either:

- Click **Scrape Now** on the dashboard or settings page, or
- Run manually:

```bash
docker compose exec sunpass python -c "
import asyncio
from sunpass.scraper.run import run_scrape
asyncio.run(run_scrape())
"
```

The initial scrape pulls the last 90 days of transactions.

## Configuration

### Port

To change the host port, edit `docker-compose.yml`:

```yaml
ports:
  - "YOUR_PORT:8080"
```

### Scrape Schedule

The schedule uses standard cron syntax (`minute hour day month day_of_week`):

| Schedule | Cron Expression |
|----------|----------------|
| Daily at 6 AM | `0 6 * * *` |
| Every 12 hours | `0 */12 * * *` |
| Weekly on Monday | `0 6 * * 1` |
| Every 6 hours | `0 */6 * * *` |

### Data Persistence

Transaction data is stored in a SQLite database at `./data/sunpass.db`, mounted as a Docker volume. Your data survives container rebuilds and restarts.

To reset all data:

```bash
rm data/sunpass.db
docker compose restart
```

## Tech Stack

| Component | Technology |
|-----------|-----------|
| Scraping | [Playwright](https://playwright.dev/) (Python, async) |
| Backend | [FastAPI](https://fastapi.tiangolo.com/) + Jinja2 |
| Interactivity | [HTMX](https://htmx.org/) |
| Charts | [Chart.js](https://www.chartjs.org/) + chartjs-plugin-datalabels |
| Tables | [DataTables](https://datatables.net/) |
| Map | [Leaflet.js](https://leafletjs.com/) + leaflet-heat |
| Database | SQLite via aiosqlite |
| Scheduling | APScheduler |
| Container | Docker + Docker Compose |

## Project Structure

```
sunpass_analytics/
├── docker-compose.yml          # Container orchestration
├── Dockerfile                  # Container build
├── pyproject.toml              # Python dependencies
├── .env.example                # Credential template
├── src/sunpass/
│   ├── main.py                 # FastAPI app + scheduler
│   ├── config.py               # Environment configuration
│   ├── plaza_coords.py         # Toll plaza lat/lng mapping
│   ├── db/
│   │   ├── models.py           # SQLite schema
│   │   └── queries.py          # Data access layer
│   ├── scraper/
│   │   ├── auth.py             # SunPass login flow
│   │   ├── vehicles.py         # Vehicle/transponder scraper
│   │   ├── transactions.py     # Transaction scraper
│   │   └── run.py              # Scrape orchestrator
│   ├── routes/                 # FastAPI route handlers
│   ├── templates/              # Jinja2 HTML templates
│   └── static/                 # CSS and JavaScript
└── data/                       # SQLite database (gitignored)
```

## License

MIT
