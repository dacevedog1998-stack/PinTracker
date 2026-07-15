from __future__ import annotations

from typing import Iterable

from database import get_connection


# =========================================================
# SKU MASTER
# =========================================================

def get_all_skus(active_only: bool = False):
    connection = get_connection()

    try:
        sql = """
            SELECT id, sku, description, pins_per_kettle, active
            FROM sku_master
        """
        parameters: tuple = ()

        if active_only:
            sql += " WHERE active = TRUE"

        sql += " ORDER BY sku"

        return connection.execute(sql, parameters).fetchall()

    finally:
        connection.close()


def upsert_sku(
    sku: str,
    description: str,
    pins_per_kettle: float,
    active: bool = True,
) -> None:
    sku = str(sku).strip().upper()
    description = str(description).strip()

    if not sku:
        raise ValueError("SKU is required.")

    if not description:
        raise ValueError("Description is required.")

    if float(pins_per_kettle) <= 0:
        raise ValueError("Pins per Kettle must be greater than zero.")

    connection = get_connection()

    try:
        connection.execute(
            """
            INSERT INTO sku_master (
                sku,
                description,
                pins_per_kettle,
                active
            )
            VALUES (%s, %s, %s, %s)
            ON CONFLICT(sku) DO UPDATE SET
                description = EXCLUDED.description,
                pins_per_kettle = EXCLUDED.pins_per_kettle,
                active = EXCLUDED.active,
                updated_at = CURRENT_TIMESTAMP
            """,
            (
                sku,
                description,
                float(pins_per_kettle),
                bool(active),
            ),
        )
        connection.commit()

    except Exception:
        connection.rollback()
        raise

    finally:
        connection.close()


def update_sku(
    original_sku: str,
    sku: str,
    description: str,
    pins_per_kettle: float,
    active: bool,
) -> None:
    original_sku = str(original_sku).strip().upper()
    sku = str(sku).strip().upper()
    description = str(description).strip()

    if not sku or not description:
        raise ValueError("SKU and Description are required.")

    if float(pins_per_kettle) <= 0:
        raise ValueError("Pins per Kettle must be greater than zero.")

    connection = get_connection()

    try:
        connection.execute(
            """
            UPDATE sku_master
            SET
                sku = %s,
                description = %s,
                pins_per_kettle = %s,
                active = %s,
                updated_at = CURRENT_TIMESTAMP
            WHERE sku = %s
            """,
            (
                sku,
                description,
                float(pins_per_kettle),
                bool(active),
                original_sku,
            ),
        )
        connection.commit()

    except Exception:
        connection.rollback()
        raise

    finally:
        connection.close()


def delete_sku(sku: str) -> None:
    connection = get_connection()

    try:
        connection.execute(
            "DELETE FROM sku_master WHERE sku = %s",
            (str(sku).strip().upper(),),
        )
        connection.commit()

    except Exception:
        connection.rollback()
        raise

    finally:
        connection.close()


# =========================================================
# DAILY PLANNING
# =========================================================

def get_planning_for_date(production_date: str):
    connection = get_connection()

    try:
        return connection.execute(
            """
            SELECT
                p.id AS planned_id,
                s.sku,
                s.description,
                s.pins_per_kettle,
                s.active,
                COALESCE(p.kettles_planned, 0) AS kettles_planned,
                COALESCE(p.expected_pins, 0) AS expected_pins
            FROM sku_master AS s
            LEFT JOIN planned_usage AS p
                ON p.sku = s.sku
                AND p.production_date = %s
            WHERE
                s.active = TRUE
                OR p.id IS NOT NULL
            ORDER BY
                CASE WHEN p.id IS NOT NULL THEN 0 ELSE 1 END,
                p.id,
                s.sku
            """,
            (production_date,),
        ).fetchall()

    finally:
        connection.close()


def get_saved_planning_for_date(production_date: str):
    connection = get_connection()

    try:
        return connection.execute(
            """
            SELECT
                p.id AS planned_id,
                p.production_date,
                s.sku,
                s.description,
                s.pins_per_kettle,
                s.active,
                p.kettles_planned,
                p.expected_pins
            FROM planned_usage AS p
            INNER JOIN sku_master AS s
                ON s.sku = p.sku
            WHERE p.production_date = %s
            ORDER BY p.id
            """,
            (production_date,),
        ).fetchall()

    finally:
        connection.close()


def save_planning_rows(
    production_date: str,
    rows: Iterable[dict],
) -> None:
    connection = get_connection()

    try:
        prepared_rows = []

        for row in rows:
            prepared_rows.append(
                {
                    "sku": str(row["SKU"]).strip().upper(),
                    "kettles": max(
                        float(row["Kettles Planned"]),
                        0.0,
                    ),
                    "expected": max(
                        float(row["Expected Pins"]),
                        0.0,
                    ),
                }
            )

        retained_skus = [row["sku"] for row in prepared_rows]

        with connection.cursor() as cursor:
            if retained_skus:
                cursor.execute(
                    """
                    DELETE FROM actual_usage
                    WHERE
                        production_date = %s
                        AND NOT (sku = ANY(%s))
                    """,
                    (production_date, retained_skus),
                )
            else:
                cursor.execute(
                    """
                    DELETE FROM actual_usage
                    WHERE production_date = %s
                    """,
                    (production_date,),
                )

            cursor.execute(
                """
                DELETE FROM planned_usage
                WHERE production_date = %s
                """,
                (production_date,),
            )

            for row in prepared_rows:
                cursor.execute(
                    """
                    INSERT INTO planned_usage (
                        production_date,
                        sku,
                        kettles_planned,
                        expected_pins
                    )
                    VALUES (%s, %s, %s, %s)
                    """,
                    (
                        production_date,
                        row["sku"],
                        row["kettles"],
                        row["expected"],
                    ),
                )

        connection.commit()

    except Exception:
        connection.rollback()
        raise

    finally:
        connection.close()


# =========================================================
# ACTUAL PRODUCTION
# =========================================================

def get_actuals_for_date(production_date: str):
    connection = get_connection()

    try:
        return connection.execute(
            """
            SELECT
                s.sku,
                s.description,
                s.pins_per_kettle,
                p.kettles_planned,
                p.expected_pins,
                COALESCE(a.yield_percent, 100) AS yield_percent,
                COALESCE(a.actual_pins, 0) AS actual_pins,
                COALESCE(a.notes, '') AS notes
            FROM planned_usage AS p
            INNER JOIN sku_master AS s
                ON s.sku = p.sku
            LEFT JOIN actual_usage AS a
                ON a.sku = p.sku
                AND a.production_date = p.production_date
            WHERE
                p.production_date = %s
                AND s.active = TRUE
            ORDER BY p.id
            """,
            (production_date,),
        ).fetchall()

    finally:
        connection.close()


def save_actual_rows(
    production_date: str,
    rows: Iterable[dict],
) -> None:
    connection = get_connection()

    try:
        with connection.cursor() as cursor:
            for row in rows:
                sku = str(row["SKU"]).strip().upper()
                actual_pins = max(
                    float(row["Actuals"]),
                    0.0,
                )
                yield_percent = min(
                    max(float(row["Yield %"]), 0.0),
                    100.0,
                )
                notes = str(
                    row.get("Notes", "") or ""
                ).strip()

                cursor.execute(
                    """
                    INSERT INTO actual_usage (
                        production_date,
                        sku,
                        actual_pins,
                        yield_percent,
                        notes
                    )
                    VALUES (%s, %s, %s, %s, %s)
                    ON CONFLICT(production_date, sku) DO UPDATE SET
                        actual_pins = EXCLUDED.actual_pins,
                        yield_percent = EXCLUDED.yield_percent,
                        notes = EXCLUDED.notes,
                        updated_at = CURRENT_TIMESTAMP
                    """,
                    (
                        production_date,
                        sku,
                        actual_pins,
                        yield_percent,
                        notes,
                    ),
                )

        connection.commit()

    except Exception:
        connection.rollback()
        raise

    finally:
        connection.close()


# =========================================================
# SUMMARY / HISTORY
# =========================================================

def get_summary_for_date(production_date: str):
    connection = get_connection()

    try:
        return connection.execute(
            """
            SELECT
                p.production_date,
                s.sku,
                s.description,
                s.pins_per_kettle,
                p.kettles_planned,
                p.expected_pins,
                COALESCE(a.yield_percent, 100) AS yield_percent,
                COALESCE(a.actual_pins, 0) AS actual_pins,
                COALESCE(a.notes, '') AS notes
            FROM planned_usage AS p
            INNER JOIN sku_master AS s
                ON s.sku = p.sku
            LEFT JOIN actual_usage AS a
                ON a.sku = p.sku
                AND a.production_date = p.production_date
            WHERE p.production_date = %s
            ORDER BY p.id
            """,
            (production_date,),
        ).fetchall()

    finally:
        connection.close()


def get_available_dates():
    connection = get_connection()

    try:
        rows = connection.execute(
            """
            SELECT DISTINCT production_date
            FROM planned_usage
            ORDER BY production_date DESC
            """
        ).fetchall()

        return [
            row["production_date"].isoformat()
            for row in rows
        ]

    finally:
        connection.close()


def get_summary_for_range(
    start_date: str,
    end_date: str,
    skus: list[str] | None = None,
):
    connection = get_connection()

    try:
        parameters: list[object] = [
            start_date,
            end_date,
        ]

        sql = """
            SELECT
                p.production_date,
                s.sku,
                s.description,
                s.pins_per_kettle,
                p.kettles_planned,
                p.expected_pins,
                COALESCE(a.yield_percent, 100) AS yield_percent,
                COALESCE(a.actual_pins, 0) AS actual_pins,
                COALESCE(a.notes, '') AS notes
            FROM planned_usage AS p
            INNER JOIN sku_master AS s
                ON s.sku = p.sku
            LEFT JOIN actual_usage AS a
                ON a.sku = p.sku
                AND a.production_date = p.production_date
            WHERE p.production_date BETWEEN %s AND %s
        """

        if skus:
            sql += " AND p.sku = ANY(%s)"
            parameters.append(skus)

        sql += " ORDER BY p.production_date DESC, p.id"

        return connection.execute(
            sql,
            tuple(parameters),
        ).fetchall()

    finally:
        connection.close()
