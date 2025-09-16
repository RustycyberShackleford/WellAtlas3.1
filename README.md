# WellAtlas v3.1 — Preseeded Gantt (EXACT page + working)

This package uses the EXACT `templates/gantt.html` you provided and wires the required API:
- `GET /api/jobs_timeline` returns customer/site/job_number, start/end, category.

Run:
  pip install -r requirements.txt
  python app.py
Open:
  http://localhost:8000/gantt

Deploy (Render/Heroku):
  web: gunicorn app:app --bind 0.0.0.0:$PORT --timeout 120
