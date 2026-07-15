from datetime import date

import streamlit as st

from database import create_database
from repository import (
    get_all_skus,
    get_available_dates,
    get_summary_for_range,
)
from ui_helpers import build_summary_dataframe


create_database()

st.set_page_config(
    page_title="History and Reports",
    page_icon="🗂️",
    layout="wide",
)

st.title("🗂️ History and Reports")
st.caption(
    "History always reflects the current saved Planning and Production data."
)

if st.button("Refresh History"):
    st.rerun()

available_dates = get_available_dates()

if not available_dates:
    st.info("No saved history is available.")
    st.stop()

minimum_date = date.fromisoformat(min(available_dates))
maximum_date = date.fromisoformat(max(available_dates))

col1, col2 = st.columns([1.3, 2])

with col1:
    selected_range = st.date_input(
        "Production Date Range",
        value=(minimum_date, maximum_date),
        min_value=minimum_date,
        max_value=maximum_date,
    )

with col2:
    all_skus = get_all_skus()
    sku_lookup = {
        row["sku"]: row["description"]
        for row in all_skus
    }

    selected_skus = st.multiselect(
        "SKU Filter",
        options=list(sku_lookup.keys()),
        format_func=lambda sku: f"{sku} - {sku_lookup[sku]}",
        placeholder="Leave empty to include all SKUs",
    )

if isinstance(selected_range, tuple):
    if len(selected_range) != 2:
        st.info("Select both a start date and an end date.")
        st.stop()

    start_date, end_date = selected_range
else:
    start_date = selected_range
    end_date = selected_range

if start_date > end_date:
    st.error("The start date cannot be after the end date.")
    st.stop()

summary_rows = get_summary_for_range(
    start_date=str(start_date),
    end_date=str(end_date),
    skus=selected_skus or None,
)

summary_df = build_summary_dataframe(
    summary_rows,
    include_date=True,
)

if summary_df.empty:
    st.info("No records match the selected filters.")
    st.stop()

total_kettles = summary_df["Kettle Planned"].sum()
total_expected = summary_df["Expected Pins"].sum()
total_new_expected = summary_df["New Expected"].sum()
total_actual = summary_df["Actuals"].sum()

weighted_yield = (
    (
        summary_df["Yield %"]
        * summary_df["Expected Pins"]
    ).sum()
    / total_expected
    if total_expected > 0
    else 0
)

metric1, metric2, metric3, metric4, metric5 = st.columns(5)

metric1.metric("Kettles Planned", f"{total_kettles:,.2f}")
metric2.metric("Expected Pins", f"{total_expected:,.2f}")
metric3.metric("Yield", f"{weighted_yield:.2f}%")
metric4.metric("New Expected", f"{total_new_expected:,.2f}")
metric5.metric("Actual Pins", f"{total_actual:,.2f}")

st.subheader("Filtered Report")

st.dataframe(
    summary_df,
    use_container_width=True,
    hide_index=True,
    column_config={
        "Kettle Planned": st.column_config.NumberColumn(
            format="%.2f",
        ),
        "Expected Pins": st.column_config.NumberColumn(
            format="%.2f",
        ),
        "Yield %": st.column_config.NumberColumn(
            format="%.2f%%",
        ),
        "New Expected": st.column_config.NumberColumn(
            format="%.2f",
        ),
        "Actuals": st.column_config.NumberColumn(
            format="%.2f",
        ),
        "Variance": st.column_config.NumberColumn(
            format="%.2f",
            help="Actual Pins minus New Expected.",
        ),
    },
)

sku_file_label = (
    "all_skus"
    if not selected_skus
    else "_".join(selected_skus)
)

st.download_button(
    "Download Filtered Report CSV",
    data=summary_df.to_csv(
        index=False,
        float_format="%.2f",
    ).encode("utf-8"),
    file_name=(
        f"pin_usage_report_"
        f"{start_date}_to_{end_date}_"
        f"{sku_file_label}.csv"
    ),
    mime="text/csv",
)
