import aiosqlite

from sunpass.config import DB_PATH

SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS vehicles (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    vehicle_id TEXT UNIQUE NOT NULL,
    friendly_name TEXT,
    make TEXT,
    model TEXT,
    year TEXT,
    color TEXT,
    license_plate TEXT,
    license_state TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS transponders (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    transponder_id TEXT UNIQUE NOT NULL,
    transponder_type TEXT,
    status TEXT,
    vehicle_id TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (vehicle_id) REFERENCES vehicles(vehicle_id)
);

CREATE TABLE IF NOT EXISTS transactions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    transaction_id TEXT UNIQUE,
    transaction_date TIMESTAMP NOT NULL,
    posted_date TIMESTAMP,
    transponder_id TEXT,
    vehicle_id TEXT,
    plaza_name TEXT,
    agency TEXT,
    amount REAL NOT NULL,
    transaction_type TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (transponder_id) REFERENCES transponders(transponder_id),
    FOREIGN KEY (vehicle_id) REFERENCES vehicles(vehicle_id)
);

CREATE TABLE IF NOT EXISTS scrape_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    started_at TIMESTAMP NOT NULL,
    completed_at TIMESTAMP,
    status TEXT NOT NULL,
    error_message TEXT,
    transactions_added INTEGER DEFAULT 0,
    vehicles_added INTEGER DEFAULT 0,
    transponders_added INTEGER DEFAULT 0
);

CREATE INDEX IF NOT EXISTS idx_transactions_date ON transactions(transaction_date);
CREATE INDEX IF NOT EXISTS idx_transactions_plaza ON transactions(plaza_name);
CREATE INDEX IF NOT EXISTS idx_transactions_vehicle ON transactions(vehicle_id);
CREATE INDEX IF NOT EXISTS idx_transactions_transponder ON transactions(transponder_id);
"""


async def get_db() -> aiosqlite.Connection:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    db = await aiosqlite.connect(str(DB_PATH))
    db.row_factory = aiosqlite.Row
    await db.execute("PRAGMA journal_mode=WAL")
    await db.execute("PRAGMA foreign_keys=ON")
    return db


async def init_db() -> None:
    db = await get_db()
    try:
        await db.executescript(SCHEMA_SQL)
        await db.commit()
    finally:
        await db.close()
