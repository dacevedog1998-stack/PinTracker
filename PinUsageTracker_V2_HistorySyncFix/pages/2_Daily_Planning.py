from datetime import date
import hmac
import os

import pandas as pd
import streamlit as st

from calculations import expected_pins
from database import create_database
from repository import (
    get_planning_for_date,
    get_saved_planning_for_date,
    save_planning_rows,
)


create_database()

st.set_page_config(
    page_title="Daily Planning",
    page_icon="📋",
    layout="wide",
)

st.title("📋 Daily Planning")
st.caption(
    "The saved plan is loaded directly from the database whenever you "
    "select a production date. A password is required to amend it."
)


def get_planning_password() -> str:
    try:
        secret_password = st.secrets.get("PLANNING_PASSWORD")
    except Exception:
        secret_password = None

    return str(
        secret_password
        or os.getenv("PLANNING_PASSWORD")
        or "admin123"
    )


def password_is_correct(password: str) -> bool:
    return hmac.compare_digest(
        str(password),
        get_planning_password(),
    )


if "planning_unlocked" not in st.session_state:
    st.session_state.planning_unlocked = False


selected_date = st.date_input(
    "Production Date",
    value=date.today(),
)

production_date = str(selected_date)

flash_message = st.session_state.pop(
    "planning_flash_message",
    None,
)

if flash_message:
    st.success(flash_message)


# =========================================================
# PASSWORD CONTROL
# =========================================================

if st.session_state.planning_unlocked:
    col1, col2 = st.columns([4, 1])

    with col1:
        st.success("Planning is unlocked for this session.")

    with col2:
        if st.button("Lock Planning"):
            st.session_state.planning_unlocked = False
            st.rerun()

else:
    with st.expander("🔒 Unlock Planning", expanded=True):
        with st.form("planning_password_form", clear_on_submit=True):
            entered_password = st.text_input(
                "Planning Password",
                type="password",
            )

            unlock_submitted = st.form_submit_button(
                "Unlock Planning",
                type="primary",
            )

        if unlock_submitted:
            if password_is_correct(entered_password):
                st.session_state.planning_unlocked = True
                st.success("Planning unlocked.")
                st.rerun()
            else:
                st.error("Incorrect password.")


# Always load the definitive saved plan directly from SQLite.
saved_rows = get_saved_planning_for_date(production_date)

saved_skus = [row["sku"] for row in saved_rows]

saved_lookup = {
    row["sku"]: {
        "description": row["description"],
        "pins_per_kettle": float(row["pins_per_kettle"]),
        "kettles_planned": float(row["kettles_planned"]),
        "expected_pins": float(row["expected_pins"]),
    }
    for row in saved_rows
}


# =========================================================
# LOCKED VIEW
# =========================================================

if not st.session_state.planning_unlocked:
    if not saved_rows:
        st.info("No planning has been saved for this date.")
        st.stop()

    read_only_df = pd.DataFrame(
        [
            {
                "SKU": row["sku"],
                "SKU Desc": row["description"],
                "Pins per Kettle": round(
                    float(row["pins_per_kettle"]),
                    2,
                ),
                "Kettle Planned": round(
                    float(row["kettles_planned"]),
                    2,
                ),
                "Expected Pins": round(
                    float(row["expected_pins"]),
                    2,
                ),
            }
            for row in saved_rows
        ]
    )

    st.subheader("Saved Daily Plan")

    st.dataframe(
        read_only_df,
        use_container_width=True,
        hide_index=True,
        column_config={
            "Pins per Kettle": st.column_config.NumberColumn(
                format="%.2f",
            ),
            "Kettle Planned": st.column_config.NumberColumn(
                format="%.2f",
            ),
            "Expected Pins": st.column_config.NumberColumn(
                format="%.2f",
            ),
        },
    )

    st.info(
        "Enter the Planning Password above to update this saved plan."
    )
    st.stop()


# =========================================================
# UNLOCKED EDITING
# =========================================================

all_rows = get_planning_for_date(production_date)

all_lookup = {
    row["sku"]: {
        "description": row["description"],
        "pins_per_kettle": float(row["pins_per_kettle"]),
        "active": bool(row["active"]),
    }
    for row in all_rows
}

available_to_add = [
    row["sku"]
    for row in all_rows
    if row["sku"] not in saved_skus and bool(row["active"])
]

version_key = f"planning_editor_version_{production_date}"

if version_key not in st.session_state:
    st.session_state[version_key] = 0

add_key = (
    f"planning_add_skus_{production_date}_"
    f"{st.session_state[version_key]}"
)

added_skus = st.multiselect(
    "Add SKUs to this Daily Plan",
    options=available_to_add,
    default=[],
    format_func=lambda sku: f"{sku} - {all_lookup[sku]['description']}",
    placeholder="Choose additional SKUs",
    key=add_key,
)

working_skus = saved_skus + [
    sku for sku in added_skus
    if sku not in saved_skus
]

if not working_skus:
    st.info(
        "No planning has been saved for this date. "
        "Choose one or more SKUs from the dropdown above."
    )
    st.stop()


planning_df = pd.DataFrame(
    [
        {
            "SKU": sku,
            "SKU Desc": (
                saved_lookup[sku]["description"]
                if sku in saved_lookup
                else all_lookup[sku]["description"]
            ),
            "Pins per Kettle": (
                saved_lookup[sku]["pins_per_kettle"]
                if sku in saved_lookup
                else all_lookup[sku]["pins_per_kettle"]
            ),
            "Kettle Planned": (
                saved_lookup[sku]["kettles_planned"]
                if sku in saved_lookup
                else 0.0
            ),
            "Expected Pins": (
                saved_lookup[sku]["expected_pins"]
                if sku in saved_lookup
                else 0.0
            ),
            "Remove": False,
        }
        for sku in working_skus
    ]
)

editor_key = (
    f"planning_editor_{production_date}_"
    f"{st.session_state[version_key]}"
)

with st.form(
    key=f"planning_form_{production_date}_{st.session_state[version_key]}",
    clear_on_submit=False,
):
    edited_df = st.data_editor(
        planning_df,
        use_container_width=True,
        hide_index=True,
        num_rows="fixed",
        disabled=[
            "SKU",
            "SKU Desc",
            "Pins per Kettle",
            "Expected Pins",
        ],
        column_config={
            "SKU": st.column_config.TextColumn(),
            "SKU Desc": st.column_config.TextColumn(),
            "Pins per Kettle": st.column_config.NumberColumn(
                format="%.2f",
            ),
            "Kettle Planned": st.column_config.NumberColumn(
                min_value=0.0,
                step=0.25,
                format="%.2f",
                required=True,
            ),
            "Expected Pins": st.column_config.NumberColumn(
                format="%.2f",
                help="Recalculated after saving.",
            ),
            "Remove": st.column_config.CheckboxColumn(
                help="Tick to remove this SKU from the selected date.",
            ),
        },
        key=editor_key,
    )

    submitted = st.form_submit_button(
        "Save / Update Daily Planning",
        type="primary",
    )


if submitted:
    rows_to_save = []

    for _, row in edited_df.iterrows():
        if bool(row["Remove"]):
            continue

        recalculated_expected = expected_pins(
            row["Kettle Planned"],
            row["Pins per Kettle"],
        )

        rows_to_save.append(
            {
                "SKU": row["SKU"],
                "Kettles Planned": row["Kettle Planned"],
                "Expected Pins": recalculated_expected,
            }
        )

    save_planning_rows(
        production_date=production_date,
        rows=rows_to_save,
    )

    st.session_state[version_key] += 1
    st.session_state["planning_flash_message"] = (
        "Daily planning was saved successfully."
    )

    st.success(
        "Daily planning was saved. It will reload automatically "
        "whenever you return to this production date."
    )
    st.rerun()


if saved_rows and st.button(
    "Clear Complete Plan for This Date",
    type="secondary",
):
    save_planning_rows(
        production_date=production_date,
        rows=[],
    )

    st.session_state[version_key] += 1
    st.session_state["planning_flash_message"] = (
        "The daily plan was cleared."
    )

    st.success("The daily plan was cleared.")
    st.rerun()
