"""Tests for database queries and models."""

import pytest

from sunpass.db.models import init_db
from sunpass.db.queries import (
    _extract_road_name,
    create_scrape_log,
    get_dashboard_summary,
    get_scrape_logs,
    get_spending_by_road,
    get_transaction_count,
    get_transactions,
    get_transponders,
    get_vehicles,
    insert_transaction,
    update_scrape_log,
    upsert_transponder,
    upsert_vehicle,
)


@pytest.fixture(autouse=True)
async def setup_db():
    """Initialize the test database schema before each test."""
    await init_db()


class TestExtractRoadName:
    """Test the pure _extract_road_name function."""

    def test_interstate(self):
        assert _extract_road_name("I-95 MIAMIGARDENS EXLN NB MP14") == "I-95"

    def test_sr_no_space(self):
        assert _extract_road_name("SR869 DEERFIELD A MAIN SB MP20") == "SR-869"

    def test_sr_with_space(self):
        assert _extract_road_name("SR 528 BEACHLINE") == "SR-528"

    def test_turnpike(self):
        assert _extract_road_name("SR91 45TH STREET MAIN NB MP104") == "SR-91 (Turnpike)"

    def test_other(self):
        assert _extract_road_name("PAYMENT & ADJUSTMENTS") == "Other"

    def test_empty(self):
        assert _extract_road_name("") == "Other"

    def test_none(self):
        assert _extract_road_name(None) == "Other"


class TestUpsertVehicle:
    async def test_insert_new(self):
        result = await upsert_vehicle("V001", friendly_name="My Car", license_plate="ABC123")
        assert result is True

    async def test_upsert_existing(self):
        await upsert_vehicle("V001", friendly_name="My Car")
        result = await upsert_vehicle("V001", friendly_name="Updated Car")
        # upsert returns True for both insert and update
        assert result is True

    async def test_get_vehicles_after_insert(self):
        await upsert_vehicle("V001", friendly_name="Car A", license_plate="AAA111")
        await upsert_vehicle("V002", friendly_name="Car B", license_plate="BBB222")
        vehicles = await get_vehicles()
        assert len(vehicles) == 2
        plates = [v["license_plate"] for v in vehicles]
        assert "AAA111" in plates
        assert "BBB222" in plates


class TestUpsertTransponder:
    async def test_insert_new(self):
        result = await upsert_transponder("T001", transponder_type="Sticker", status="Active")
        assert result is True

    async def test_get_transponders(self):
        await upsert_vehicle("V001", friendly_name="Car A", license_plate="AAA111")
        await upsert_transponder(
            "T001", transponder_type="Sticker", status="Active", vehicle_id="V001"
        )
        transponders = await get_transponders()
        assert len(transponders) == 1
        assert transponders[0]["transponder_id"] == "T001"
        assert transponders[0]["friendly_name"] == "Car A"


class TestInsertTransaction:
    async def test_insert(self):
        result = await insert_transaction(
            transaction_date="2024-01-15 08:30:00",
            amount=3.50,
            transaction_id="TXN001",
            plaza_name="I-95 Main Plaza",
        )
        assert result is True

    async def test_duplicate_skipped(self):
        await insert_transaction(
            transaction_date="2024-01-15 08:30:00",
            amount=3.50,
            transaction_id="TXN001",
        )
        result = await insert_transaction(
            transaction_date="2024-01-15 09:00:00",
            amount=5.00,
            transaction_id="TXN001",
        )
        assert result is False

    async def test_null_transaction_id_allows_duplicates(self):
        r1 = await insert_transaction(
            transaction_date="2024-01-15 08:30:00",
            amount=3.50,
            transaction_id=None,
        )
        r2 = await insert_transaction(
            transaction_date="2024-01-15 09:00:00",
            amount=5.00,
            transaction_id=None,
        )
        assert r1 is True
        assert r2 is True


class TestGetTransactions:
    async def test_empty_db(self):
        txns = await get_transactions()
        assert txns == []

    async def test_returns_data(self):
        await insert_transaction(
            transaction_date="2024-01-15 08:30:00",
            amount=3.50,
            transaction_id="TXN001",
            plaza_name="I-95 Main",
        )
        txns = await get_transactions()
        assert len(txns) == 1
        assert txns[0]["amount"] == 3.50

    async def test_date_filter(self):
        await insert_transaction(
            transaction_date="2024-01-10 08:00:00",
            amount=2.00,
            transaction_id="TXN_OLD",
        )
        await insert_transaction(
            transaction_date="2024-01-20 08:00:00",
            amount=4.00,
            transaction_id="TXN_NEW",
        )
        txns = await get_transactions(start_date="2024-01-15")
        assert len(txns) == 1
        assert txns[0]["transaction_id"] == "TXN_NEW"

    async def test_vehicle_filter(self):
        await upsert_vehicle("V001", friendly_name="Car A")
        await upsert_vehicle("V002", friendly_name="Car B")
        await insert_transaction(
            transaction_date="2024-01-15 08:00:00",
            amount=3.00,
            transaction_id="TXN_A",
            vehicle_id="V001",
        )
        await insert_transaction(
            transaction_date="2024-01-15 09:00:00",
            amount=5.00,
            transaction_id="TXN_B",
            vehicle_id="V002",
        )
        txns = await get_transactions(vehicle_id="V001")
        assert len(txns) == 1
        assert txns[0]["vehicle_id"] == "V001"

    async def test_vehicle_label_from_join(self):
        await upsert_vehicle("V001", friendly_name="My Car")
        await insert_transaction(
            transaction_date="2024-01-15 08:00:00",
            amount=3.00,
            transaction_id="TXN_A",
            vehicle_id="V001",
        )
        txns = await get_transactions()
        assert txns[0]["vehicle_label"] == "My Car"


class TestGetTransactionCount:
    async def test_empty(self):
        count = await get_transaction_count()
        assert count == 0

    async def test_with_data(self):
        await insert_transaction(
            transaction_date="2024-01-15 08:00:00",
            amount=3.00,
            transaction_id="TXN_A",
        )
        await insert_transaction(
            transaction_date="2024-01-16 08:00:00",
            amount=4.00,
            transaction_id="TXN_B",
        )
        count = await get_transaction_count()
        assert count == 2

    async def test_filtered_count(self):
        await insert_transaction(
            transaction_date="2024-01-10 08:00:00",
            amount=2.00,
            transaction_id="TXN_OLD",
        )
        await insert_transaction(
            transaction_date="2024-01-20 08:00:00",
            amount=4.00,
            transaction_id="TXN_NEW",
        )
        count = await get_transaction_count(start_date="2024-01-15")
        assert count == 1


class TestSpendingByRoad:
    async def test_aggregation(self):
        await insert_transaction(
            transaction_date="2024-01-15 08:00:00",
            amount=3.00,
            transaction_id="TXN_A",
            plaza_name="I-95 MIAMIGARDENS EXLN NB MP14",
        )
        await insert_transaction(
            transaction_date="2024-01-15 09:00:00",
            amount=2.50,
            transaction_id="TXN_B",
            plaza_name="I-95 GOLDEN GLADES SB MP21",
        )
        data = await get_spending_by_road()
        assert len(data) == 1
        assert data[0]["road"] == "I-95"
        assert data[0]["total"] == 5.50
        assert data[0]["count"] == 2


class TestScrapeLog:
    async def test_create_and_update(self):
        log_id = await create_scrape_log()
        assert log_id is not None

        await update_scrape_log(
            log_id,
            status="success",
            transactions_added=10,
            vehicles_added=2,
            transponders_added=3,
        )

        logs = await get_scrape_logs(limit=1)
        assert len(logs) == 1
        assert logs[0]["status"] == "success"
        assert logs[0]["transactions_added"] == 10

    async def test_failed_log(self):
        log_id = await create_scrape_log()
        await update_scrape_log(log_id, status="failed", error_message="Connection timeout")

        logs = await get_scrape_logs()
        assert logs[0]["status"] == "failed"
        assert logs[0]["error_message"] == "Connection timeout"


class TestDashboardSummary:
    async def test_empty_db(self):
        summary = await get_dashboard_summary()
        assert summary["month_total"] == 0
        assert summary["year_total"] == 0
        assert summary["vehicle_count"] == 0
        assert summary["transponder_count"] == 0
        assert summary["last_scrape"] is None

    async def test_with_data(self):
        await upsert_vehicle("V001")
        await upsert_transponder("T001")

        summary = await get_dashboard_summary()
        assert summary["vehicle_count"] == 1
        assert summary["transponder_count"] == 1
