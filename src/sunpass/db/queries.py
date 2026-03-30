from datetime import datetime
from typing import Any

import aiosqlite

from sunpass.db.models import get_db


async def upsert_vehicle(
    vehicle_id: str,
    friendly_name: str | None = None,
    make: str | None = None,
    model: str | None = None,
    year: str | None = None,
    color: str | None = None,
    license_plate: str | None = None,
    license_state: str | None = None,
) -> bool:
    """Upsert a vehicle. Returns True if a new row was inserted."""
    db = await get_db()
    try:
        cursor = await db.execute(
            """INSERT INTO vehicles (vehicle_id, friendly_name, make, model, year, color, license_plate, license_state)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(vehicle_id) DO UPDATE SET
                friendly_name=excluded.friendly_name, make=excluded.make, model=excluded.model,
                year=excluded.year, color=excluded.color, license_plate=excluded.license_plate,
                license_state=excluded.license_state, updated_at=CURRENT_TIMESTAMP""",
            (vehicle_id, friendly_name, make, model, year, color, license_plate, license_state),
        )
        await db.commit()
        return cursor.rowcount > 0
    finally:
        await db.close()


async def upsert_transponder(
    transponder_id: str,
    transponder_type: str | None = None,
    status: str | None = None,
    vehicle_id: str | None = None,
) -> bool:
    """Upsert a transponder. Returns True if a new row was inserted."""
    db = await get_db()
    try:
        cursor = await db.execute(
            """INSERT INTO transponders (transponder_id, transponder_type, status, vehicle_id)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(transponder_id) DO UPDATE SET
                transponder_type=excluded.transponder_type, status=excluded.status,
                vehicle_id=excluded.vehicle_id, updated_at=CURRENT_TIMESTAMP""",
            (transponder_id, transponder_type, status, vehicle_id),
        )
        await db.commit()
        return cursor.rowcount > 0
    finally:
        await db.close()


async def insert_transaction(
    transaction_date: str,
    amount: float,
    transaction_id: str | None = None,
    posted_date: str | None = None,
    transponder_id: str | None = None,
    vehicle_id: str | None = None,
    plaza_name: str | None = None,
    agency: str | None = None,
    transaction_type: str | None = None,
) -> bool:
    """Insert a transaction. Returns True if inserted (skips duplicates)."""
    db = await get_db()
    try:
        try:
            await db.execute(
                """INSERT INTO transactions
                (transaction_id, transaction_date, posted_date, transponder_id,
                 vehicle_id, plaza_name, agency, amount, transaction_type)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    transaction_id,
                    transaction_date,
                    posted_date,
                    transponder_id,
                    vehicle_id,
                    plaza_name,
                    agency,
                    amount,
                    transaction_type,
                ),
            )
            await db.commit()
            return True
        except aiosqlite.IntegrityError:
            return False
    finally:
        await db.close()


async def get_transactions(
    start_date: str | None = None,
    end_date: str | None = None,
    vehicle_id: str | None = None,
    transponder_id: str | None = None,
    plaza_name: str | None = None,
    limit: int = 500,
    offset: int = 0,
) -> list[dict[str, Any]]:
    """Query transactions with optional filters."""
    db = await get_db()
    try:
        conditions = []
        params: list[Any] = []
        if start_date:
            conditions.append("t.transaction_date >= ?")
            params.append(start_date)
        if end_date:
            conditions.append("t.transaction_date <= ?")
            params.append(end_date)
        if vehicle_id:
            conditions.append("t.vehicle_id = ?")
            params.append(vehicle_id)
        if transponder_id:
            conditions.append("t.transponder_id = ?")
            params.append(transponder_id)
        if plaza_name:
            conditions.append("t.plaza_name = ?")
            params.append(plaza_name)

        where = f"WHERE {' AND '.join(conditions)}" if conditions else ""
        query = f"""SELECT t.*,
                    COALESCE(v.friendly_name, v.license_plate, t.vehicle_id) as vehicle_label
                    FROM transactions t
                    LEFT JOIN vehicles v ON t.vehicle_id = v.vehicle_id
                    {where}
                    ORDER BY t.transaction_date DESC LIMIT ? OFFSET ?"""
        params.extend([limit, offset])

        cursor = await db.execute(query, params)
        rows = await cursor.fetchall()
        return [dict(row) for row in rows]
    finally:
        await db.close()


async def get_transaction_count(
    start_date: str | None = None,
    end_date: str | None = None,
    vehicle_id: str | None = None,
    transponder_id: str | None = None,
    plaza_name: str | None = None,
) -> int:
    """Count transactions with optional filters."""
    db = await get_db()
    try:
        conditions = []
        params: list[Any] = []
        if start_date:
            conditions.append("transaction_date >= ?")
            params.append(start_date)
        if end_date:
            conditions.append("transaction_date <= ?")
            params.append(end_date)
        if vehicle_id:
            conditions.append("vehicle_id = ?")
            params.append(vehicle_id)
        if transponder_id:
            conditions.append("transponder_id = ?")
            params.append(transponder_id)
        if plaza_name:
            conditions.append("plaza_name = ?")
            params.append(plaza_name)

        where = f"WHERE {' AND '.join(conditions)}" if conditions else ""
        cursor = await db.execute(
            f"SELECT COUNT(*) as cnt FROM transactions {where}", params
        )
        row = await cursor.fetchone()
        return row["cnt"] if row else 0
    finally:
        await db.close()


async def get_vehicles() -> list[dict[str, Any]]:
    db = await get_db()
    try:
        cursor = await db.execute("SELECT * FROM vehicles ORDER BY license_plate")
        rows = await cursor.fetchall()
        return [dict(row) for row in rows]
    finally:
        await db.close()


async def get_transponders() -> list[dict[str, Any]]:
    db = await get_db()
    try:
        cursor = await db.execute(
            """SELECT t.*, v.friendly_name, v.license_plate, v.make, v.model
            FROM transponders t
            LEFT JOIN vehicles v ON t.vehicle_id = v.vehicle_id
            ORDER BY t.transponder_id"""
        )
        rows = await cursor.fetchall()
        return [dict(row) for row in rows]
    finally:
        await db.close()


async def get_spending_by_plaza(
    start_date: str | None = None, end_date: str | None = None
) -> list[dict[str, Any]]:
    db = await get_db()
    try:
        conditions = ["amount > 0"]
        params: list[Any] = []
        if start_date:
            conditions.append("transaction_date >= ?")
            params.append(start_date)
        if end_date:
            conditions.append("transaction_date <= ?")
            params.append(end_date)
        where = f"WHERE {' AND '.join(conditions)}"
        cursor = await db.execute(
            f"""SELECT plaza_name, SUM(amount) as total, COUNT(*) as count
            FROM transactions {where}
            GROUP BY plaza_name ORDER BY total DESC""",
            params,
        )
        rows = await cursor.fetchall()
        return [dict(row) for row in rows]
    finally:
        await db.close()


async def get_spending_by_vehicle(
    start_date: str | None = None, end_date: str | None = None
) -> list[dict[str, Any]]:
    db = await get_db()
    try:
        conditions = ["amount > 0"]
        params: list[Any] = []
        if start_date:
            conditions.append("t.transaction_date >= ?")
            params.append(start_date)
        if end_date:
            conditions.append("t.transaction_date <= ?")
            params.append(end_date)
        where = f"WHERE {' AND '.join(conditions)}"
        cursor = await db.execute(
            f"""SELECT t.vehicle_id, v.license_plate, v.friendly_name, v.make, v.model,
                SUM(t.amount) as total, COUNT(*) as count
            FROM transactions t
            LEFT JOIN vehicles v ON t.vehicle_id = v.vehicle_id
            {where}
            GROUP BY t.vehicle_id ORDER BY total DESC""",
            params,
        )
        rows = await cursor.fetchall()
        return [dict(row) for row in rows]
    finally:
        await db.close()


async def get_spending_by_transponder(
    start_date: str | None = None, end_date: str | None = None
) -> list[dict[str, Any]]:
    db = await get_db()
    try:
        conditions = ["amount > 0"]
        params: list[Any] = []
        if start_date:
            conditions.append("t.transaction_date >= ?")
            params.append(start_date)
        if end_date:
            conditions.append("t.transaction_date <= ?")
            params.append(end_date)
        where = f"WHERE {' AND '.join(conditions)}"
        cursor = await db.execute(
            f"""SELECT t.transponder_id, v.friendly_name, v.license_plate,
                SUM(t.amount) as total, COUNT(*) as count
            FROM transactions t
            LEFT JOIN vehicles v ON t.transponder_id = v.vehicle_id
            {where}
            GROUP BY t.transponder_id ORDER BY total DESC""",
            params,
        )
        rows = await cursor.fetchall()
        return [dict(row) for row in rows]
    finally:
        await db.close()


async def get_spending_by_month(
    start_date: str | None = None, end_date: str | None = None
) -> list[dict[str, Any]]:
    db = await get_db()
    try:
        conditions = ["amount > 0"]
        params: list[Any] = []
        if start_date:
            conditions.append("transaction_date >= ?")
            params.append(start_date)
        if end_date:
            conditions.append("transaction_date <= ?")
            params.append(end_date)
        where = f"WHERE {' AND '.join(conditions)}"
        cursor = await db.execute(
            f"""SELECT strftime('%Y-%m', transaction_date) as month,
                SUM(amount) as total, COUNT(*) as count
            FROM transactions {where}
            GROUP BY month ORDER BY month""",
            params,
        )
        rows = await cursor.fetchall()
        return [dict(row) for row in rows]
    finally:
        await db.close()


async def get_spending_by_day_of_week(
    start_date: str | None = None, end_date: str | None = None
) -> list[dict[str, Any]]:
    db = await get_db()
    try:
        conditions = ["amount > 0"]
        params: list[Any] = []
        if start_date:
            conditions.append("transaction_date >= ?")
            params.append(start_date)
        if end_date:
            conditions.append("transaction_date <= ?")
            params.append(end_date)
        where = f"WHERE {' AND '.join(conditions)}"
        cursor = await db.execute(
            f"""SELECT CAST(strftime('%w', transaction_date) AS INTEGER) as dow,
                SUM(amount) as total, COUNT(*) as count
            FROM transactions {where}
            GROUP BY dow ORDER BY dow""",
            params,
        )
        rows = await cursor.fetchall()
        day_names = ["Sunday", "Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"]
        return [{"day": day_names[row["dow"]], "total": row["total"], "count": row["count"]} for row in rows]
    finally:
        await db.close()


async def get_daily_spending_by_vehicle(
    start_date: str | None = None, end_date: str | None = None
) -> list[dict[str, Any]]:
    """Get daily spending broken down by vehicle for stacked bar chart."""
    db = await get_db()
    try:
        conditions = ["t.amount > 0"]
        params: list[Any] = []
        if start_date:
            conditions.append("t.transaction_date >= ?")
            params.append(start_date)
        if end_date:
            conditions.append("t.transaction_date <= ?")
            params.append(end_date)
        where = f"WHERE {' AND '.join(conditions)}"
        cursor = await db.execute(
            f"""SELECT date(t.transaction_date) as day,
                t.vehicle_id,
                COALESCE(v.friendly_name, v.license_plate, t.vehicle_id) as vehicle_label,
                SUM(t.amount) as total
            FROM transactions t
            LEFT JOIN vehicles v ON t.vehicle_id = v.vehicle_id
            {where}
            GROUP BY day, t.vehicle_id
            ORDER BY day""",
            params,
        )
        rows = await cursor.fetchall()
        return [dict(row) for row in rows]
    finally:
        await db.close()


async def get_dashboard_summary() -> dict[str, Any]:
    db = await get_db()
    try:
        now = datetime.now()
        month_start = now.strftime("%Y-%m-01")
        year_start = now.strftime("%Y-01-01")

        cursor = await db.execute(
            "SELECT COALESCE(SUM(amount), 0) as total FROM transactions WHERE amount > 0 AND transaction_date >= ?",
            (month_start,),
        )
        row = await cursor.fetchone()
        month_total = row["total"] if row else 0

        cursor = await db.execute(
            "SELECT COALESCE(SUM(amount), 0) as total FROM transactions WHERE amount > 0 AND transaction_date >= ?",
            (year_start,),
        )
        row = await cursor.fetchone()
        year_total = row["total"] if row else 0

        cursor = await db.execute("SELECT COUNT(*) as cnt FROM vehicles")
        row = await cursor.fetchone()
        vehicle_count = row["cnt"] if row else 0

        cursor = await db.execute("SELECT COUNT(*) as cnt FROM transponders")
        row = await cursor.fetchone()
        transponder_count = row["cnt"] if row else 0

        cursor = await db.execute(
            "SELECT * FROM scrape_log ORDER BY started_at DESC LIMIT 1"
        )
        last_scrape = await cursor.fetchone()

        return {
            "month_total": month_total,
            "year_total": year_total,
            "vehicle_count": vehicle_count,
            "transponder_count": transponder_count,
            "last_scrape": dict(last_scrape) if last_scrape else None,
        }
    finally:
        await db.close()


async def get_filter_options() -> dict[str, list]:
    """Get distinct values for filter dropdowns with friendly labels."""
    db = await get_db()
    try:
        cursor = await db.execute(
            """SELECT DISTINCT t.vehicle_id, v.friendly_name, v.license_plate
            FROM transactions t
            LEFT JOIN vehicles v ON t.vehicle_id = v.vehicle_id
            WHERE t.vehicle_id IS NOT NULL
            ORDER BY COALESCE(v.friendly_name, v.license_plate, t.vehicle_id)"""
        )
        vehicles = []
        for row in await cursor.fetchall():
            label = row["friendly_name"] or row["license_plate"] or row["vehicle_id"]
            vehicles.append({"id": row["vehicle_id"], "label": label})

        cursor = await db.execute(
            """SELECT DISTINCT t.transponder_id, v.friendly_name, v.license_plate
            FROM transactions t
            LEFT JOIN vehicles v ON t.transponder_id = v.vehicle_id
            WHERE t.transponder_id IS NOT NULL
            ORDER BY COALESCE(v.friendly_name, v.license_plate, t.transponder_id)"""
        )
        transponders = []
        for row in await cursor.fetchall():
            label = row["friendly_name"] or row["license_plate"] or row["transponder_id"]
            transponders.append({"id": row["transponder_id"], "label": label})

        cursor = await db.execute(
            "SELECT DISTINCT plaza_name FROM transactions WHERE plaza_name IS NOT NULL ORDER BY plaza_name"
        )
        plazas = [row["plaza_name"] for row in await cursor.fetchall()]

        return {"vehicles": vehicles, "transponders": transponders, "plazas": plazas}
    finally:
        await db.close()


async def create_scrape_log() -> int:
    db = await get_db()
    try:
        cursor = await db.execute(
            "INSERT INTO scrape_log (started_at, status) VALUES (CURRENT_TIMESTAMP, 'running')"
        )
        await db.commit()
        return cursor.lastrowid
    finally:
        await db.close()


async def update_scrape_log(
    log_id: int,
    status: str,
    error_message: str | None = None,
    transactions_added: int = 0,
    vehicles_added: int = 0,
    transponders_added: int = 0,
):
    db = await get_db()
    try:
        await db.execute(
            """UPDATE scrape_log SET
                completed_at=CURRENT_TIMESTAMP, status=?, error_message=?,
                transactions_added=?, vehicles_added=?, transponders_added=?
            WHERE id=?""",
            (status, error_message, transactions_added, vehicles_added, transponders_added, log_id),
        )
        await db.commit()
    finally:
        await db.close()


async def get_scrape_logs(limit: int = 20) -> list[dict[str, Any]]:
    db = await get_db()
    try:
        cursor = await db.execute(
            "SELECT * FROM scrape_log ORDER BY started_at DESC LIMIT ?", (limit,)
        )
        rows = await cursor.fetchall()
        return [dict(row) for row in rows]
    finally:
        await db.close()
