# WellAtlasV4 — Gold UI + Scheduling (Empty DB)

- Gold header + buttons and American flag background baked in (`static/background.jpg`).
- Map page with MapTiler Hybrid/Streets (via MAPTILER_KEY) and OSM fallback.
- Global / site / job Gantt views.
- Job calendar + iCal export.
- Crew module and crew scheduling calendar.
- Empty SQLite DB at `data/wellatlas.db` with all tables but no rows.

Env vars:
- MAPTILER_KEY — MapTiler API key (optional; if unset, uses OpenStreetMap tiles).
- SECRET_KEY — Flask session secret (set to any random string in production).

Run locally:
  pip install -r requirements.txt
  python app.py

Procfile uses:
  web: gunicorn app:app --bind 0.0.0.0:$PORT --timeout 120
