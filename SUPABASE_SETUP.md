# Persistent deployment setup

This version uses Supabase PostgreSQL instead of a local SQLite file.
The data remains available when Streamlit restarts, sleeps, or redeploys.

## Keep the same Streamlit URL

Your current deployment uses:

- Repository: `pintracker`
- Branch: `main`
- Main file path: `PinUsageTracker_V2_HistorySyncFix/app.py`

Keep the folder name and main file path exactly the same. Replace the
contents of the existing `PinUsageTracker_V2_HistorySyncFix` folder with
the contents of this folder, commit, and push to the same `main` branch.

Streamlit monitors the same GitHub coordinates and updates the existing
deployment. The URL stays the same.

## 1. Create a Supabase project

1. Sign in to Supabase.
2. Create a new project.
3. Save the database password.
4. In the project, click **Connect**.
5. Copy a pooler connection URI. For Streamlit Cloud, the Transaction
   pooler URI on port 6543 is appropriate.
6. Add `?sslmode=require` if the copied URI does not already contain an
   SSL setting.

The URI looks similar to:

```text
postgresql://postgres.PROJECT:PASSWORD@REGION.pooler.supabase.com:6543/postgres?sslmode=require
```

Replace `[YOUR-PASSWORD]` in the copied URI with the real database
password. URL-encode special password characters when necessary.

## 2. Add Streamlit Cloud secrets

Open the existing Streamlit app, then:

1. Click **Manage app**.
2. Open **Settings**.
3. Open **Secrets**.
4. Paste:

```toml
DATABASE_URL = "YOUR_SUPABASE_POOLER_CONNECTION_STRING"
PLANNING_PASSWORD = "YOUR_PLANNING_PASSWORD"
```

5. Save the settings.

Never place the real connection string in GitHub.

## 3. Replace the folder without changing the deployment path

In your local GitHub repository:

1. Open the existing folder:

```text
PinUsageTracker_V2_HistorySyncFix
```

2. Delete its old application files.
3. Copy all files from this new folder into it.
4. Do not rename the folder.
5. Do not delete the repository's hidden `.git` folder.

Run:

```bash
git add -A
git commit -m "Move Pin Tracker to persistent Supabase database"
git push origin main
```

Streamlit automatically sees the commit and redeploys the same app.

## 4. Local testing

Create:

```text
.streamlit/secrets.toml
```

Copy the content of `secrets.toml.example`, then add your real
credentials.

Run:

```bash
python -m pip install -r requirements.txt
python -m streamlit run app.py
```

## Database tables

The app creates the required tables automatically at startup. The
`supabase_schema.sql` file is also included if you prefer to create or
inspect the schema in Supabase SQL Editor.

## Important

The old local `data/pins.db` file is no longer used. Do not upload
database passwords or `.streamlit/secrets.toml` to GitHub.
