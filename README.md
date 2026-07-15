# Pin Usage Tracker V2 — Persistent Edition

This application tracks:

- SKU Master
- Pins per Kettle
- Daily Planning
- Expected Pins
- Production Yield
- New Expected Pins
- Actual Pins
- Date and SKU history filters
- Planning password protection

## Persistent storage

This edition uses a remote PostgreSQL database such as Supabase.
It does not store production data in the temporary Streamlit server
filesystem.

Read `SUPABASE_SETUP.md` before deployment.

## Run locally

```bash
python -m pip install -r requirements.txt
python -m streamlit run app.py
```
