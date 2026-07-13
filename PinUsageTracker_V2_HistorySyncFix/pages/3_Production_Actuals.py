from datetime import date

import pandas as pd
import streamlit as st

from calculations import new_expected_pins
from database import create_database
from repository import (
    get_actuals_for_date,
    save_actual_rows,
)


create_database()

st.set_page_config(
    page_title="Production Actuals",
    page_icon="🏭",
    layout="wide",
)

st.title("🏭 Production Actuals")
st.caption(
    "Only SKUs planned for the selected date are shown. "
    "Planning data is locked. Yield and Actual Pins are editable."
)

selected_date = st.date_input(
    "Production Date",
    value=date.today(),
)

rows = get_actuals_for_date(str(selected_date))

if not rows:
    st.warning(
        "No SKUs were planned for this date. "
        "Create or update the plan in Daily Planning first."
    )
    st.stop()

production_df = pd.DataFrame(
    [
        {
            "SKU": row["sku"],
            "SKU Desc": row["description"],
            "Kettle Planned": round(float(row["kettles_planned"]), 2),
            "Expected Pins": round(float(row["expected_pins"]), 2),
            "Yield %": round(float(row["yield_percent"]), 2),
            "New Expected": round(
                new_expected_pins(
                    row["expected_pins"],
                    row["yield_percent"],
                ),
                2,
            ),
            "Actuals": round(float(row["actual_pins"]), 2),
        }
        for row in rows
    ]
)

version_key = f"production_editor_version_{selected_date}"

if version_key not in st.session_state:
    st.session_state[version_key] = 0

editor_key = (
    f"production_editor_{selected_date}_"
    f"{st.session_state[version_key]}"
)

with st.form(
    key=f"production_form_{selected_date}_{st.session_state[version_key]}",
    clear_on_submit=False,
):
    edited_df = st.data_editor(
        production_df,
        use_container_width=True,
        hide_index=True,
        num_rows="fixed",
        disabled=[
            "SKU",
            "SKU Desc",
            "Kettle Planned",
            "Expected Pins",
            "New Expected",
        ],
        column_config={
            "SKU": st.column_config.TextColumn(),
            "SKU Desc": st.column_config.TextColumn(),
            "Kettle Planned": st.column_config.NumberColumn(
                format="%.2f",
            ),
            "Expected Pins": st.column_config.NumberColumn(
                format="%.2f",
            ),
            "Yield %": st.column_config.NumberColumn(
                min_value=0.0,
                max_value=100.0,
                step=0.1,
                format="%.2f",
                required=True,
            ),
            "New Expected": st.column_config.NumberColumn(
                format="%.2f",
                help=(
                    "Expected Pins multiplied by Yield %. "
                    "It updates after Save / Update."
                ),
            ),
            "Actuals": st.column_config.NumberColumn(
                "Actual Pins",
                min_value=0.0,
                step=0.25,
                format="%.2f",
                required=True,
            ),
        },
        key=editor_key,
    )

    submitted = st.form_submit_button(
        "Save / Update Production Actuals",
        type="primary",
    )

if submitted:
    edited_df["New Expected"] = edited_df.apply(
        lambda row: round(
            new_expected_pins(
                row["Expected Pins"],
                row["Yield %"],
            ),
            2,
        ),
        axis=1,
    )

    save_actual_rows(
        production_date=str(selected_date),
        rows=edited_df.to_dict("records"),
    )

    st.session_state[version_key] += 1
    st.success(
        "Production actuals were saved. "
        "New Expected was recalculated from the saved Yield."
    )
    st.rerun()
