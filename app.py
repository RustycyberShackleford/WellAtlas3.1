import os, sqlite3
from flask import Flask, render_template, request, jsonify, abort

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

# Preseeded page data: customer/site/job/category/start/end
@app.get('/api/jobs_timeline')
def api_jobs_timeline():
    c=db();cur=c.cursor()
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
    for r in rows:
        if r.get('start') and not isinstance(r['start'], str): r['start'] = str(r['start'])
        if r.get('end') and not isinstance(r['end'], str): r['end'] = str(r['end'])
    return jsonify(rows)

# Map helpers
@app.get('/api/customers')
def api_customers():
    c=db();cur=c.cursor();cur.execute('SELECT id,name FROM customers ORDER BY name')
    rows=[dict(r) for r in cur.fetchall()]; c.close()
    return jsonify(rows)

@app.get('/api/sites')
def api_sites():
    q = (request.args.get('q') or '').strip()
    customer_id = request.args.get('customer_id')
    c=db();cur=c.cursor()
    sql = 'SELECT sites.*, customers.name as customer FROM sites JOIN customers ON customers.id=sites.customer_id'
    wh=[]; params=[]
    if customer_id: wh.append('customers.id=?'); params.append(customer_id)
    if q:
        like=f'%{q}%'
        wh.append('(sites.name LIKE ? OR customers.name LIKE ? OR sites.description LIKE ?)'); params+= [like, like, like]
    if wh: sql += ' WHERE ' + ' AND '.join(wh)
    sql += ' ORDER BY customers.name, sites.name'
    cur.execute(sql, params)
    rows=[dict(r) for r in cur.fetchall()]; c.close()
    return jsonify(rows)

@app.get('/healthz')
def healthz(): return 'ok'

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.getenv("PORT","8000")), debug=True)
