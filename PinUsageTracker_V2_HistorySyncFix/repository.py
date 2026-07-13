from __future__ import annotations

from typing import Iterable

from database import get_connection


# =========================================================
# SKU MASTER
# =========================================================

def get_all_skus(active_only: bool = False):
    connection = get_connection()

    sql = """
        SELECT id, sku, description, pins_per_kettle, active
        FROM sku_master
    """

    parameters = ()

    if active_only:
        sql += " WHERE active = 1"

    sql += " ORDER BY sku"

    rows = connection.execute(sql, parameters).fetchall()
    connection.close()

    return rows


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

    connection.execute(
        """
        INSERT INTO sku_master (
            sku,
            description,
            pins_per_kettle,
            active
        )
        VALUES (?, ?, ?, ?)
        ON CONFLICT(sku) DO UPDATE SET
            description = excluded.description,
            pins_per_kettle = excluded.pins_per_kettle,
            active = excluded.active,
            updated_at = CURRENT_TIMESTAMP
        """,
        (
            sku,
            description,
            float(pins_per_kettle),
            1 if active else 0,
        ),
    )

    connection.commit()
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

    connection.execute(
        """
        UPDATE sku_master
        SET
            sku = ?,
            description = ?,
            pins_per_kettle = ?,
            active = ?,
            updated_at = CURRENT_TIMESTAMP
        WHERE sku = ?
        """,
        (
            sku,
            description,
            float(pins_per_kettle),
            1 if active else 0,
            original_sku,
        ),
    )

    connection.commit()
    connection.close()


def delete_sku(sku: str) -> None:
    connection = get_connection()

    connection.execute(
        "DELETE FROM sku_master WHERE sku = ?",
        (str(sku).strip().upper(),),
    )

    connection.commit()
    connection.close()


# =========================================================
# DAILY PLANNING
# =========================================================

def get_planning_for_date(production_date: str):
    """
    Return every active SKU plus any SKU already saved in the plan.

    A saved SKU remains visible even if it is later marked inactive.
    planned_id identifies rows that are already stored for the date.
    """
    connection = get_connection()

    rows = connection.execute(
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
            AND p.production_date = ?
        WHERE
            s.active = 1
            OR p.id IS NOT NULL
        ORDER BY
            CASE WHEN p.id IS NOT NULL THEN 0 ELSE 1 END,
            p.id,
            s.sku
        """,
        (production_date,),
    ).fetchall()

    connection.close()

    return rows


def get_saved_planning_for_date(production_date: str):
    """
    Return only the plan rows actually saved for the selected date,
    in the same order in which they were saved.
    """
    connection = get_connection()

    rows = connection.execute(
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
        WHERE p.production_date = ?
        ORDER BY p.id
        """,
        (production_date,),
    ).fetchall()

    connection.close()

    return rows

def save_planning_rows(
    production_date: str,
    rows: Iterable[dict],
) -> None:
    """
    Replace the complete plan for the selected date.

    Actual records are preserved only for SKUs that remain in the plan.
    If the complete day is removed, its actual records are removed too.
    """
    connection = get_connection()
    cursor = connection.cursor()

    try:
        prepared_rows = []

        for row in rows:
            sku = str(row["SKU"]).strip().upper()
            kettles = max(float(row["Kettles Planned"]), 0.0)
            expected = max(float(row["Expected Pins"]), 0.0)

            prepared_rows.append(
                {
                    "sku": sku,
                    "kettles": kettles,
                    "expected": expected,
                }
            )

        retained_skus = [row["sku"] for row in prepared_rows]

        # Remove actual records that no longer belong to the updated plan.
        if retained_skus:
            placeholders = ", ".join("?" for _ in retained_skus)

            cursor.execute(
                f"""
                DELETE FROM actual_usage
                WHERE
                    production_date = ?
                    AND sku NOT IN ({placeholders})
                """,
                (production_date, *retained_skus),
            )
        else:
            cursor.execute(
                """
                DELETE FROM actual_usage
                WHERE production_date = ?
                """,
                (production_date,),
            )

        # Replace the complete planning table for this date.
        cursor.execute(
            """
            DELETE FROM planned_usage
            WHERE production_date = ?
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
                VALUES (?, ?, ?, ?)
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
    """
    Return only SKUs that were planned for the selected production date.
    Planning data is included for reference in Production Actuals.
    """
    connection = get_connection()

    rows = connection.execute(
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
            p.production_date = ?
            AND s.active = 1
        ORDER BY p.id
        """,
        (production_date,),
    ).fetchall()

    connection.close()

    return rows

def save_actual_rows(
    production_date: str,
    rows: Iterable[dict],
) -> None:
    connection = get_connection()
    cursor = connection.cursor()

    for row in rows:
        sku = str(row["SKU"]).strip().upper()
        actual_pins = max(float(row["Actuals"]), 0.0)
        yield_percent = min(max(float(row["Yield %"]), 0.0), 100.0)
        notes = str(row.get("Notes", "") or "").strip()

        cursor.execute(
            """
            INSERT INTO actual_usage (
                production_date,
                sku,
                actual_pins,
                yield_percent,
                notes
            )
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(production_date, sku) DO UPDATE SET
                actual_pins = excluded.actual_pins,
                yield_percent = excluded.yield_percent,
                notes = excluded.notes,
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
    connection.close()


# =========================================================
# SUMMARY / HISTORY
# =========================================================

def get_summary_for_date(production_date: str):
    """
    Return the current saved plan and its matching actual records.

    Obsolete actual-only rows are intentionally excluded.
    """
    connection = get_connection()

    rows = connection.execute(
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
        WHERE p.production_date = ?
        ORDER BY p.id
        """,
        (production_date,),
    ).fetchall()

    connection.close()

    return rows

def get_available_dates():
    """
    Return only dates that currently have a saved daily plan.
    """
    connection = get_connection()

    rows = connection.execute(
        """
        SELECT DISTINCT production_date
        FROM planned_usage
        ORDER BY production_date DESC
        """
    ).fetchall()

    connection.close()

    return [row["production_date"] for row in rows]

def get_summary_for_range(
    start_date: str,
    end_date: str,
    skus: list[str] | None = None,
):
    """
    Return planned and actual results between two inclusive dates.

    When skus is empty or None, all SKUs in the selected date range
    are returned.
    """
    connection = get_connection()

    parameters: list[object] = [start_date, end_date]

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
        WHERE p.production_date BETWEEN ? AND ?
    """

    if skus:
        placeholders = ", ".join("?" for _ in skus)
        sql += f" AND p.sku IN ({placeholders})"
        parameters.extend(skus)

    sql += " ORDER BY p.production_date DESC, p.id"

    rows = connection.execute(
        sql,
        tuple(parameters),
    ).fetchall()

    connection.close()

    return rows
