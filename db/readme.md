# NetFX Onboarding Tool

## Overview
A small Tkinter desktop app with SQLite backend that lists Clients and lets you open per-client tabs with Merchants and Client Ratesheets. The UI is modular (sidebar, tabs, per-client sub-tabs).

## Run
1. (Optional) Create a virtualenv:
   - `python -m venv venv`
   - activate (`venv\Scripts\activate` on Windows or `source venv/bin/activate` on macOS/Linux)
2. Run:
   - `python main.py`

## Notes
- DB file `netfx.db` will be created in the project root on first run.
- Foreign keys are enabled (`PRAGMA foreign_keys = ON`) so deletes cascade according to model definitions.
- You can find sample data pre-seeded for clients, merchants, and ratesheets.

## Files
- `config.py` — app constants
- `db/` — DB models and DBManager with CRUD methods
- `ui/` — UI modules: sidebar, tabs, client + per-client merchants & ratesheets views
- `main.py` — app bootstrap / wiring
