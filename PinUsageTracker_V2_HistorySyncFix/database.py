import sqlite3
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
DATABASE_PATH = DATA_DIR / "pins.db"


def get_connection() -> sqlite3.Connection:
    DATA_DIR.mkdir(parents=True, exist_ok=True)

    connection = sqlite3.connect(DATABASE_PATH)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")

    return connection


def create_database() -> None:
    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS sku_master (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            sku TEXT NOT NULL UNIQUE,
            description TEXT NOT NULL,
            pins_per_kettle REAL NOT NULL CHECK (pins_per_kettle > 0),
            active INTEGER NOT NULL DEFAULT 1 CHECK (active IN (0, 1)),
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        )
        """
    )

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS planned_usage (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            production_date TEXT NOT NULL,
            sku TEXT NOT NULL,
            kettles_planned REAL NOT NULL DEFAULT 0 CHECK (kettles_planned >= 0),
            expected_pins REAL NOT NULL DEFAULT 0 CHECK (expected_pins >= 0),
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            UNIQUE (production_date, sku),
            FOREIGN KEY (sku) REFERENCES sku_master(sku)
                ON UPDATE CASCADE
                ON DELETE RESTRICT
        )
        """
    )

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS actual_usage (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            production_date TEXT NOT NULL,
            sku TEXT NOT NULL,
            actual_pins REAL NOT NULL DEFAULT 0 CHECK (actual_pins >= 0),
            yield_percent REAL NOT NULL DEFAULT 100 CHECK (
                yield_percent >= 0 AND yield_percent <= 100
            ),
            notes TEXT NOT NULL DEFAULT '',
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            UNIQUE (production_date, sku),
            FOREIGN KEY (sku) REFERENCES sku_master(sku)
                ON UPDATE CASCADE
                ON DELETE RESTRICT
        )
        """
    )

    cursor.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_planned_date
        ON planned_usage(production_date)
        """
    )

    cursor.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_actual_date
        ON actual_usage(production_date)
        """
    )

    connection.commit()
    connection.close()


if __name__ == "__main__":
    create_database()
    print(f"Database ready: {DATABASE_PATH}")
