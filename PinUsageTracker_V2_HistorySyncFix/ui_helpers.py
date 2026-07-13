from __future__ import annotations

import pandas as pd

from calculations import (
    format_number,
    new_expected_pins,
    pin_variance,
)


def build_summary_dataframe(
    rows,
    include_date: bool = False,
) -> pd.DataFrame:
    records = []

    for row in rows:
        expected = float(row["expected_pins"])
        yield_percent = float(row["yield_percent"])
        actual = float(row["actual_pins"])
        new_expected = new_expected_pins(expected, yield_percent)

        record = {
            "SKU": row["sku"],
            "SKU Desc": row["description"],
            "Kettle Planned": format_number(row["kettles_planned"]),
            "Expected Pins": format_number(expected),
            "Yield %": format_number(yield_percent),
            "New Expected": format_number(new_expected),
            "Actuals": format_number(actual),
            "Variance": format_number(
                pin_variance(actual, new_expected)
            ),
        }

        if include_date:
            record = {
                "Production Date": row["production_date"],
                **record,
            }

        records.append(record)

    columns = [
        "SKU",
        "SKU Desc",
        "Kettle Planned",
        "Expected Pins",
        "Yield %",
        "New Expected",
        "Actuals",
        "Variance",
    ]

    if include_date:
        columns.insert(0, "Production Date")

    return pd.DataFrame(records, columns=columns)
