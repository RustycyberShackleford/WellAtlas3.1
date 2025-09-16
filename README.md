# WellAtlas v3.1 CLEAN
- Correct background path: `/static/background.jpg` (wavy flag included)
- Working map (OpenStreetMap tiles, no API key required)
- EXACT preseeded `templates/gantt.html` (your upload) with `/api/jobs_timeline` wired
- Flask exposes `app` so Gunicorn starts cleanly

## Run
pip install -r requirements.txt
python app.py
# http://localhost:8000 (map) and http://localhost:8000/gantt (preseeded chart)

## Deploy
web: gunicorn app:app --bind 0.0.0.0:$PORT --timeout 120
