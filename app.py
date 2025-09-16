import os, sqlite3
from flask import Flask, render_template, jsonify, abort

BASE_DIR = os.path.dirname(__file__)
DATA_DIR = os.path.join(BASE_DIR, "data")
os.makedirs(DATA_DIR, exist_ok=True)
DB_PATH = os.path.join(DATA_DIR, "wellatlas.db")

app = Flask(__name__)
app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY","dev-secret")

def db():
    c = sqlite3.connect(DB_PATH, check_same_thread=False)
    c.row_factory = sqlite3.Row
    return c

@app.get('/')
def index():
    return render_template('index.html')

@app.get('/gantt')
def gantt():
    return render_template('gantt.html')

@app.get('/customers')
def customers():
    c=db();cur=c.cursor();cur.execute('SELECT * FROM customers ORDER BY name')
    rows=[dict(r) for r in cur.fetchall()]; c.close()
    return render_template('customers.html', customers=rows)

# EXACT preseeded page expects this endpoint:
@app.get('/api/jobs_timeline')
def api_jobs_timeline():
    c=db();cur=c.cursor()
    # Join customers, sites, jobs with required fields
    cur.execute('''
      SELECT customers.name as customer,
             sites.name as site,
             jobs.job_number as job_number,
             jobs.job_category as category,
             jobs.start_date as start,
             jobs.end_date as end
      FROM jobs
      JOIN sites ON jobs.site_id = sites.id
      JOIN customers ON sites.customer_id = customers.id
      WHERE jobs.start_date IS NOT NULL AND jobs.end_date IS NOT NULL
      ORDER BY date(jobs.start_date)
    ''')
    rows=[dict(r) for r in cur.fetchall()]
    c.close()
    # Coerce dates to strings if needed
    for r in rows:
        if r.get('start') and not isinstance(r['start'], str): r['start'] = str(r['start'])
        if r.get('end') and not isinstance(r['end'], str): r['end'] = str(r['end'])
    return jsonify(rows)

@app.get('/healthz')
def healthz(): return 'ok'

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.getenv("PORT","8000")), debug=True)
