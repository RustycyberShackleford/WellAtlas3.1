# WellAtlas 3.0.0 Gold — Satellite MapTiler + Gantt (Flag Embedded)
- Home: MapTiler Satellite (hybrid). Set MAPTILER_KEY for tiles; OSM fallback if not set.
- Background baked in: /static/background.jpg (waving flag).
- Seeded DB so Gantt charts populate immediately.

## Env
MAPTILER_KEY=<your_maptiler_api_key>
SECRET_KEY=<any string>

## Run
pip install -r requirements.txt
python app.py

## Deploy (Render/Heroku)
web: gunicorn app:app --bind 0.0.0.0:$PORT --timeout 120
