from datetime import date
from pathlib import Path

import streamlit as st

from database import create_database
from repository import get_summary_for_date
from ui_helpers import build_summary_dataframe


BASE_DIR = Path(__file__).resolve().parent
FAVICON_PATH = BASE_DIR / "favicon.png"


create_database()


st.set_page_config(
    page_title="Pin Usage Tracker",
    page_icon=str(FAVICON_PATH),
    layout="wide",
)


col_logo, col_title = st.columns(
    [1, 12],
    vertical_alignment="center",
)

with col_logo:
    st.image(
        str(FAVICON_PATH),
        width=55,
    )

with col_title:
    st.title("Pin Usage Tracker")


st.caption(
    "Planned kettles, expected pins, yield-adjusted expectation "
    "and actual pin usage."
)


selected_date = st.date_input(
    "Production Date",
    value=date.today(),
)


summary_rows = get_summary_for_date(
    str(selected_date)
)

summary_df = build_summary_dataframe(
    summary_rows
)


if summary_df.empty:
    st.info(
        "No planning or actual production has been saved for this date. "
        "Use Daily Planning and Production Actuals from the left menu."
    )
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


col1, col2, col3, col4, col5 = st.columns(5)

col1.metric(
    "Kettles Planned",
    f"{total_kettles:,.2f}",
)

col2.metric(
    "Expected Pins",
    f"{total_expected:,.2f}",
)

col3.metric(
    "Yield",
    f"{weighted_yield:.2f}%",
)

col4.metric(
    "New Expected",
    f"{total_new_expected:,.2f}",
)

col5.metric(
    "Actual Pins",
    f"{total_actual:,.2f}",
    f"{total_actual - total_new_expected:+,.2f}",
)


st.subheader("Daily Summary")


st.dataframe(
    summary_df,
    width="stretch",
    hide_index=True,
    column_config={
        "Kettle Planned": st.column_config.NumberColumn(
            format="%.2f"
        ),
        "Expected Pins": st.column_config.NumberColumn(
            format="%.2f"
        ),
        "Yield %": st.column_config.NumberColumn(
            format="%.2f%%"
        ),
        "New Expected": st.column_config.NumberColumn(
            format="%.2f"
        ),
        "Actuals": st.column_config.NumberColumn(
            format="%.2f"
        ),
        "Variance": st.column_config.NumberColumn(
            format="%.2f",
            help="Actual Pins minus New Expected.",
        ),
    },
)


st.download_button(
    label="Download Summary CSV",
    data=summary_df.to_csv(
        index=False,
        float_format="%.2f",
    ).encode("utf-8"),
    file_name=f"pin_usage_summary_{selected_date}.csv",
    mime="text/csv",
)
