# Pin Usage Tracker V2

A simple Streamlit application for daily pin planning and actual usage.

## Core summary

The main table contains:

- SKU
- SKU Desc
- Kettle Planned
- Expected Pins
- Yield %
- New Expected
- Actuals
- Variance

## Calculation logic

```text
Expected Pins = Kettles Planned × Pins per Kettle

New Expected = Expected Pins ÷ (Yield % / 100)

Variance = Actual Pins - New Expected
```

## Run the project

Open a terminal in the project folder and run:

```bash
python -m pip install -r requirements.txt
python -m streamlit run app.py
```

The SQLite database is created automatically at:

```text
data/pins.db
```

## Recommended order

1. Open **SKU Master** and create SKUs.
2. Open **Daily Planning** and enter Kettles Planned.
3. Open **Production Actuals** and enter Actual Pins and Yield.
4. Review the dashboard or History.


## SKU list options

The SKU Master page now supports:

- Adding one SKU manually
- Pasting a complete SKU list
- Uploading Excel or CSV
- Editing and deleting existing SKUs

## Daily Planning selection

Daily Planning now includes a multi-select dropdown so you can choose only the SKUs needed for the selected production date.


## Production Actuals

Production Actuals now shows only the SKUs included in Daily Planning for the selected date.

Visible columns:

- SKU
- SKU Desc
- Kettle Planned
- Expected Pins
- Yield %
- New Expected
- Actuals

Only Yield % and Actuals can be edited in this section.


## Stable table editing

Daily Planning and Production Actuals now use Streamlit forms.

- Pressing Enter while editing no longer clears the entered table.
- Data is written to SQLite with Save / Update.
- Daily Planning replaces the complete plan for the selected date.
- Production New Expected recalculates after Save / Update.


## Yield correction

New Expected now uses:

```text
New Expected = Expected Pins × (Yield % / 100)
```

All displayed report values use two decimal places.

## History filters

History and Reports now supports:

- Start date and end date
- One SKU, multiple SKUs, or all SKUs
- Filtered CSV download


## Planning password

Daily Planning is read-only until it is unlocked with a password.

The local ZIP starts with:

```text
admin123
```

Change it in:

```text
.streamlit/secrets.toml
```

For Streamlit Community Cloud, add this in the app's Secrets settings:

```toml
PLANNING_PASSWORD = "your_secure_password"
```

The real `secrets.toml` file is excluded from GitHub through `.gitignore`.


## Saved planning persistence

Daily Planning now reloads the definitive saved plan directly from SQLite
whenever a production date is selected.

- Existing saved SKUs always appear first and keep their saved order.
- Additional SKUs can be added through the dropdown.
- A SKU can be removed by ticking the Remove column.
- Returning to a previously saved date reloads its complete plan.

When installing an updated version over an existing project, preserve:

```text
data/pins.db
```

That file contains your saved SKU Master, Planning, Production Actuals,
and History data.


## History synchronization

History now always reflects the current saved plan.

- Updating a planned SKU updates History immediately.
- Removing a SKU from a day removes its obsolete Actual record.
- Clearing a complete day removes that day from History.
- Actual data for SKUs that remain in the plan is preserved.
- The History page includes a Refresh History button.
