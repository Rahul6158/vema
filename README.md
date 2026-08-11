# Vema Store Manager

Flask + SQLite store-management application for Vema.

## Quick start

```bash
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
```

Copy `.env.example` to `.env`, set a secure `SECRET_KEY`, then start the app:

```bash
python run.py
```

Open `http://localhost:5000/login`. Application data is stored in `instance/data.db`.

## Legacy data migration

The app no longer reads from the `google_drive` JSON folder. Its data has been imported into SQLite. The folder remains only as a recoverable backup; after you verify the data, you can archive or delete it.

To rerun the import intentionally:

```bash
python migrate_legacy_json.py
```
