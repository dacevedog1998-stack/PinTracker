import pandas as pd
import streamlit as st

from database import create_database
from repository import (
    delete_sku,
    get_all_skus,
    update_sku,
    upsert_sku,
)


create_database()

st.set_page_config(
    page_title="SKU Master",
    page_icon="📦",
    layout="wide",
)

st.title("📦 SKU Master")
st.caption(
    "Add SKUs individually, paste a complete list, or upload an Excel/CSV file."
)

tab1, tab2, tab3 = st.tabs(
    ["Add One SKU", "Paste SKU List", "Upload Excel / CSV"]
)


# =========================================================
# ADD ONE SKU
# =========================================================

with tab1:
    with st.form("add_sku_form", clear_on_submit=True):
        col1, col2, col3, col4 = st.columns([1.2, 2.5, 1.2, 1])

        with col1:
            sku = st.text_input("SKU")

        with col2:
            description = st.text_input("Description")

        with col3:
            pins_per_kettle = st.number_input(
                "Pins per Kettle",
                min_value=0.01,
                value=1.0,
                step=0.25,
            )

        with col4:
            active = st.checkbox("Active", value=True)

        submitted = st.form_submit_button("Add / Update SKU")

        if submitted:
            try:
                upsert_sku(
                    sku=sku,
                    description=description,
                    pins_per_kettle=pins_per_kettle,
                    active=active,
                )
                st.success("SKU saved.")
                st.rerun()
            except Exception as error:
                st.error(str(error))


# =========================================================
# PASTE SKU LIST
# =========================================================

with tab2:
    st.write(
        "Paste one SKU per line using this format:"
    )
    st.code("SKU,Description,Pins per Kettle")

    pasted_text = st.text_area(
        "SKU List",
        height=220,
        placeholder=(
            "10001,Beef Pie,14\n"
            "10002,Pepper Steak Pie,13.5\n"
            "10003,Beef Sausage Roll,16"
        ),
    )

    if st.button("Import Pasted List", type="primary"):
        imported = 0
        errors = []

        for line_number, line in enumerate(
            pasted_text.splitlines(),
            start=1,
        ):
            clean_line = line.strip()

            if not clean_line:
                continue

            parts = [part.strip() for part in clean_line.split(",")]

            if len(parts) != 3:
                errors.append(
                    f"Line {line_number}: use SKU,Description,Pins per Kettle"
                )
                continue

            sku_code, sku_description, pins_value = parts

            try:
                upsert_sku(
                    sku=sku_code,
                    description=sku_description,
                    pins_per_kettle=float(pins_value),
                    active=True,
                )
                imported += 1
            except Exception as error:
                errors.append(f"Line {line_number}: {error}")

        if imported:
            st.success(f"{imported} SKU(s) imported.")

        if errors:
            st.error("\n".join(errors))

        if imported and not errors:
            st.rerun()


# =========================================================
# UPLOAD EXCEL OR CSV
# =========================================================

with tab3:
    st.write(
        "Required columns: SKU, Description, Pins per Kettle. "
        "An optional Active column may also be included."
    )

    template_df = pd.DataFrame(
        [
            {
                "SKU": "10001",
                "Description": "Beef Pie",
                "Pins per Kettle": 14,
                "Active": True,
            }
        ]
    )

    st.download_button(
        "Download CSV Template",
        data=template_df.to_csv(index=False).encode("utf-8"),
        file_name="sku_master_template.csv",
        mime="text/csv",
    )

    uploaded_file = st.file_uploader(
        "Upload SKU Master",
        type=["xlsx", "xls", "csv"],
    )

    if uploaded_file is not None:
        try:
            if uploaded_file.name.lower().endswith(".csv"):
                upload_df = pd.read_csv(uploaded_file)
            else:
                upload_df = pd.read_excel(uploaded_file)

            st.subheader("File Preview")
            st.dataframe(
                upload_df,
                use_container_width=True,
                hide_index=True,
            )

            required_columns = {
                "SKU",
                "Description",
                "Pins per Kettle",
            }

            missing_columns = required_columns - set(upload_df.columns)

            if missing_columns:
                st.error(
                    "Missing column(s): "
                    + ", ".join(sorted(missing_columns))
                )
            elif st.button("Import Uploaded SKU List", type="primary"):
                imported = 0
                errors = []

                for index, row in upload_df.iterrows():
                    try:
                        active_value = row.get("Active", True)

                        if pd.isna(active_value):
                            active_value = True

                        if isinstance(active_value, str):
                            active_value = (
                                active_value.strip().lower()
                                not in {"false", "no", "0", "inactive"}
                            )

                        upsert_sku(
                            sku=row["SKU"],
                            description=row["Description"],
                            pins_per_kettle=float(row["Pins per Kettle"]),
                            active=bool(active_value),
                        )
                        imported += 1
                    except Exception as error:
                        errors.append(
                            f"Row {index + 2}: {error}"
                        )

                if imported:
                    st.success(f"{imported} SKU(s) imported.")

                if errors:
                    st.error("\n".join(errors))

                if imported and not errors:
                    st.rerun()

        except Exception as error:
            st.error(f"Could not read the file: {error}")


# =========================================================
# EXISTING SKU LIST
# =========================================================

st.divider()
st.subheader("Existing SKUs")

rows = get_all_skus()

if not rows:
    st.info("No SKUs have been created yet.")
    st.stop()

original_df = pd.DataFrame(
    [
        {
            "Original SKU": row["sku"],
            "SKU": row["sku"],
            "Description": row["description"],
            "Pins per Kettle": float(row["pins_per_kettle"]),
            "Active": bool(row["active"]),
            "Delete": False,
        }
        for row in rows
    ]
)

edited_df = st.data_editor(
    original_df,
    use_container_width=True,
    hide_index=True,
    disabled=["Original SKU"],
    column_config={
        "Original SKU": st.column_config.TextColumn("Original SKU"),
        "SKU": st.column_config.TextColumn(required=True),
        "Description": st.column_config.TextColumn(required=True),
        "Pins per Kettle": st.column_config.NumberColumn(
            min_value=0.01,
            step=0.25,
            required=True,
        ),
        "Active": st.column_config.CheckboxColumn(),
        "Delete": st.column_config.CheckboxColumn(),
    },
    key="sku_editor",
)

if st.button("Save SKU Changes", type="primary"):
    errors = []

    for _, row in edited_df.iterrows():
        try:
            if bool(row["Delete"]):
                delete_sku(row["Original SKU"])
            else:
                update_sku(
                    original_sku=row["Original SKU"],
                    sku=row["SKU"],
                    description=row["Description"],
                    pins_per_kettle=row["Pins per Kettle"],
                    active=bool(row["Active"]),
                )
        except Exception as error:
            errors.append(f"{row['Original SKU']}: {error}")

    if errors:
        st.error("\n".join(errors))
    else:
        st.success("SKU changes saved.")
        st.rerun()
