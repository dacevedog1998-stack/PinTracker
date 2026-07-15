from __future__ import annotations

import os

import psycopg
import streamlit as st
from psycopg.rows import dict_row


def get_database_url() -> str:
    """
    Read the persistent PostgreSQL connection string.

    Streamlit Cloud:
        Add DATABASE_URL in App settings > Secrets.

    Local computer:
        Add DATABASE_URL to .streamlit/secrets.toml or define it as an
        environment variable.
    """
    database_url = None

    try:
        database_url = st.secrets.get("DATABASE_URL")
    except Exception:
        database_url = None

    database_url = database_url or os.getenv("DATABASE_URL")

    if not database_url:
        raise RuntimeError(
            "DATABASE_URL is missing. Add your Supabase PostgreSQL "
            "connection string to Streamlit Secrets."
        )

    database_url = str(database_url).strip()

    # Some dashboards copy the URI with postgres://.
    if database_url.startswith("postgres://"):
        database_url = "postgresql://" + database_url[len("postgres://"):]

    return database_url


def get_connection() -> psycopg.Connection:
    return psycopg.connect(
        get_database_url(),
        row_factory=dict_row,
        connect_timeout=15,
    )


def create_database() -> None:
    """
    Create the application tables in the persistent PostgreSQL database.
    Running this repeatedly is safe.
    """
    connection = get_connection()

    try:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS sku_master (
                    id BIGSERIAL PRIMARY KEY,
                    sku TEXT NOT NULL UNIQUE,
                    description TEXT NOT NULL,
                    pins_per_kettle DOUBLE PRECISION NOT NULL
                        CHECK (pins_per_kettle > 0),
                    active BOOLEAN NOT NULL DEFAULT TRUE,
                    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
                )
                """
            )

            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS planned_usage (
                    id BIGSERIAL PRIMARY KEY,
                    production_date DATE NOT NULL,
                    sku TEXT NOT NULL,
                    kettles_planned DOUBLE PRECISION NOT NULL DEFAULT 0
                        CHECK (kettles_planned >= 0),
                    expected_pins DOUBLE PRECISION NOT NULL DEFAULT 0
                        CHECK (expected_pins >= 0),
                    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE (production_date, sku),
                    CONSTRAINT planned_usage_sku_fk
                        FOREIGN KEY (sku)
                        REFERENCES sku_master(sku)
                        ON UPDATE CASCADE
                        ON DELETE RESTRICT
                )
                """
            )

            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS actual_usage (
                    id BIGSERIAL PRIMARY KEY,
                    production_date DATE NOT NULL,
                    sku TEXT NOT NULL,
                    actual_pins DOUBLE PRECISION NOT NULL DEFAULT 0
                        CHECK (actual_pins >= 0),
                    yield_percent DOUBLE PRECISION NOT NULL DEFAULT 100
                        CHECK (
                            yield_percent >= 0
                            AND yield_percent <= 100
                        ),
                    notes TEXT NOT NULL DEFAULT '',
                    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE (production_date, sku),
                    CONSTRAINT actual_usage_sku_fk
                        FOREIGN KEY (sku)
                        REFERENCES sku_master(sku)
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

    except Exception:
        connection.rollback()
        raise

    finally:
        connection.close()


if __name__ == "__main__":
    create_database()
    print("Persistent PostgreSQL database is ready.")
