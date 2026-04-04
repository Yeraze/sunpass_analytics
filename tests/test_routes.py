"""Tests for FastAPI API routes."""

import pytest
from httpx import ASGITransport, AsyncClient

from sunpass.db.models import init_db
from sunpass.db.queries import insert_transaction
from sunpass.main import app


@pytest.fixture(autouse=True)
async def setup_db():
    await init_db()


@pytest.fixture
async def client():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


class TestDashboardRoute:
    async def test_dashboard_returns_html(self, client):
        resp = await client.get("/")
        assert resp.status_code == 200
        assert "text/html" in resp.headers["content-type"]


class TestTransactionsRoute:
    async def test_transactions_page(self, client):
        resp = await client.get("/transactions")
        assert resp.status_code == 200
        assert "text/html" in resp.headers["content-type"]

    async def test_transaction_table_fragment(self, client):
        resp = await client.get("/fragments/transaction-table")
        assert resp.status_code == 200

    async def test_export_csv_empty(self, client):
        resp = await client.get("/transactions/export")
        assert resp.status_code == 200
        assert "text/csv" in resp.headers["content-type"]
        assert "Date" in resp.text  # CSV header

    async def test_export_csv_with_data(self, client):
        await insert_transaction(
            transaction_date="2024-01-15 08:30:00",
            amount=3.50,
            transaction_id="TXN_EXPORT",
            plaza_name="I-95 Main",
        )
        resp = await client.get("/transactions/export")
        assert resp.status_code == 200
        assert "I-95 Main" in resp.text


class TestAnalyticsRoutes:
    async def test_analytics_page(self, client):
        resp = await client.get("/analytics")
        assert resp.status_code == 200

    async def test_by_plaza_empty(self, client):
        resp = await client.get("/api/analytics/by-plaza")
        assert resp.status_code == 200
        data = resp.json()
        assert "labels" in data
        assert "values" in data
        assert data["labels"] == []

    async def test_by_plaza_with_data(self, client):
        await insert_transaction(
            transaction_date="2024-01-15 08:30:00",
            amount=3.50,
            transaction_id="TXN_P1",
            plaza_name="I-95 Main",
        )
        resp = await client.get("/api/analytics/by-plaza")
        data = resp.json()
        assert "I-95 Main" in data["labels"]
        assert 3.50 in data["values"]

    async def test_by_road(self, client):
        await insert_transaction(
            transaction_date="2024-01-15 08:30:00",
            amount=3.50,
            transaction_id="TXN_R1",
            plaza_name="I-95 MIAMIGARDENS EXLN NB MP14",
        )
        resp = await client.get("/api/analytics/by-road")
        data = resp.json()
        assert "I-95" in data["labels"]

    async def test_by_vehicle(self, client):
        resp = await client.get("/api/analytics/by-vehicle")
        assert resp.status_code == 200
        assert resp.json()["labels"] == []

    async def test_by_transponder(self, client):
        resp = await client.get("/api/analytics/by-transponder")
        assert resp.status_code == 200

    async def test_by_month(self, client):
        resp = await client.get("/api/analytics/by-month")
        assert resp.status_code == 200

    async def test_by_day_of_week(self, client):
        resp = await client.get("/api/analytics/by-day-of-week")
        assert resp.status_code == 200

    async def test_daily_by_vehicle(self, client):
        resp = await client.get("/api/analytics/daily-by-vehicle")
        assert resp.status_code == 200
        data = resp.json()
        assert "labels" in data
        assert "datasets" in data

    async def test_color_map(self, client):
        resp = await client.get("/api/color-map")
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, dict)

    async def test_date_range_filter(self, client):
        await insert_transaction(
            transaction_date="2024-01-10 08:00:00",
            amount=2.00,
            transaction_id="TXN_EARLY",
            plaza_name="I-95 Main",
        )
        await insert_transaction(
            transaction_date="2024-06-15 08:00:00",
            amount=5.00,
            transaction_id="TXN_LATE",
            plaza_name="SR869 Main",
        )
        resp = await client.get("/api/analytics/by-plaza?start_date=2024-06-01")
        data = resp.json()
        assert len(data["labels"]) == 1
        assert "SR869 Main" in data["labels"]


class TestVehiclesRoute:
    async def test_vehicles_page(self, client):
        resp = await client.get("/vehicles")
        assert resp.status_code == 200
        assert "text/html" in resp.headers["content-type"]


class TestMapRoute:
    async def test_map_page(self, client):
        resp = await client.get("/map")
        assert resp.status_code == 200

    async def test_heatmap_empty(self, client):
        resp = await client.get("/api/map/heatmap")
        assert resp.status_code == 200
        data = resp.json()
        assert "points" in data
        assert "unmatched" in data

    async def test_heatmap_with_data(self, client):
        await insert_transaction(
            transaction_date="2024-01-15 08:30:00",
            amount=3.50,
            transaction_id="TXN_MAP1",
            plaza_name="I-95 MIAMIGARDENS EXLN NB MP14",
        )
        resp = await client.get("/api/map/heatmap")
        data = resp.json()
        # Should have either a matched point or an unmatched entry
        assert len(data["points"]) + len(data["unmatched"]) >= 1


class TestSettingsRoute:
    async def test_settings_page(self, client):
        resp = await client.get("/settings")
        assert resp.status_code == 200
        assert "text/html" in resp.headers["content-type"]

    async def test_scrape_status(self, client):
        resp = await client.get("/api/scrape-status")
        assert resp.status_code == 200
