import os, sqlite3, secrets, datetime, csv, io
from flask import Flask, render_template, request, jsonify, abort, redirect, url_for, Response

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

# -------- Core pages from 3.0 (kept) --------
@app.get('/')
def index():
    return render_template('index.html', maptiler_key=os.getenv('MAPTILER_KEY',''))

@app.get('/customers')
def customers_index():
    c=db();cur=c.cursor();cur.execute('SELECT * FROM customers ORDER BY name')
    rows=[dict(r) for r in cur.fetchall()]; c.close()
    return render_template('customers.html', customers=rows)

@app.route('/customers/new', methods=['GET','POST'])
def new_customer():
    if request.method=='GET': return render_template('new_customer.html')
    name = request.form.get('name'); 
    if not name: abort(400)
    phone = request.form.get('phone',''); email = request.form.get('email','')
    address = request.form.get('address',''); notes = request.form.get('notes','')
    c=db();cur=c.cursor()
    cur.execute('INSERT INTO customers(name,address,phone,email,notes) VALUES(?,?,?,?,?)',(name,address,phone,email,notes))
    cid = cur.lastrowid; c.commit(); c.close()
    return redirect(url_for('customer_detail', cid=cid))

@app.get('/customer/<int:cid>')
def customer_detail(cid):
    c=db();cur=c.cursor()
    cur.execute('SELECT * FROM customers WHERE id=?',(cid,)); customer=cur.fetchone()
    if not customer: c.close(); abort(404)
    cur.execute('SELECT * FROM sites WHERE customer_id=? ORDER BY name',(cid,))
    sites=[dict(r) for r in cur.fetchall()]; c.close()
    return render_template('customer_detail.html', customer=dict(customer), sites=sites)

@app.get('/site/<int:site_id>')
def site_detail(site_id):
    c=db();cur=c.cursor()
    cur.execute('SELECT sites.*, customers.name as customer FROM sites JOIN customers ON customers.id=sites.customer_id WHERE sites.id=?',(site_id,))
    site=cur.fetchone()
    if not site: c.close(); abort(404)
    cur.execute('SELECT * FROM jobs WHERE site_id=? ORDER BY job_number',(site_id,))
    jobs=[dict(r) for r in cur.fetchall()]; c.close()
    return render_template('site_detail.html', site=dict(site), jobs=jobs)

@app.route('/site/<int:site_id>/jobs/new', methods=['GET','POST'])
def new_job(site_id):
    c=db();cur=c.cursor()
    cur.execute('SELECT sites.*, customers.name as customer FROM sites JOIN customers ON customers.id=sites.customer_id WHERE sites.id=?',(site_id,))
    site=cur.fetchone()
    if not site: c.close(); abort(404)
    if request.method=='GET':
        c.close(); return render_template('new_job.html', site=dict(site))
    f = request.form
    cur.execute('''INSERT INTO jobs(site_id,job_number,job_category,description,depth_ft,casing_diameter_in,pump_hp,flow_rate_gpm,static_level_ft,drawdown_ft,start_date,end_date,install_date,status)
                   VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?)''',
        (site_id, f.get('job_number'), f.get('job_category'), f.get('description',''),
         f.get('depth_ft') or None, f.get('casing_diameter_in') or None, f.get('pump_hp') or None,
         f.get('flow_rate_gpm') or None, f.get('static_level_ft') or None, f.get('drawdown_ft') or None,
         f.get('start_date'), f.get('end_date'), f.get('end_date'), f.get('status','Scheduled')))
    c.commit(); c.close()
    return redirect(url_for('site_detail', site_id=site_id))

@app.get('/site/<int:site_id>/job/<int:job_id>')
def job_detail(site_id,job_id):
    c=db();cur=c.cursor()
    cur.execute('SELECT * FROM jobs WHERE id=?',(job_id,)); job=cur.fetchone()
    if not job or job['site_id']!=site_id: c.close(); abort(404)
    cur.execute('SELECT sites.*, customers.name as customer FROM sites JOIN customers ON customers.id=sites.customer_id WHERE sites.id=?',(site_id,))
    site=cur.fetchone()
    cur.execute('SELECT * FROM job_notes WHERE job_id=? ORDER BY datetime(created_at) DESC',(job_id,))
    notes=[dict(r) for r in cur.fetchall()]; c.close()
    return render_template('job_detail.html', site=dict(site), job=dict(job), notes=notes)

@app.get('/jobs')
def jobs_index():
    c=db();cur=c.cursor()
    cur.execute('''
      SELECT jobs.*, sites.name as site, sites.id as site_id, customers.name as customer
      FROM jobs JOIN sites ON jobs.site_id=sites.id JOIN customers ON customers.id=sites.customer_id
      ORDER BY jobs.job_number
    ''')
    rows=[dict(r) for r in cur.fetchall()]; c.close()
    return render_template('jobs.html', jobs=rows)

# -------- v3.1: Gantt page & APIs --------
@app.get('/gantt')
def gantt():
    return render_template('gantt.html')

@app.get('/api/jobs')
def api_jobs():
    # Filters: customer_id, site_id, category, status, start_after, end_before, q
    args = request.args
    c = db(); cur = c.cursor()
    sql = '''
      SELECT jobs.*, sites.name as site_name, sites.id as site_id,
             customers.id as customer_id, customers.name as customer_name
      FROM jobs
      JOIN sites ON jobs.site_id=sites.id
      JOIN customers ON customers.id=sites.customer_id
    '''
    wh = []; params = []
    if args.get("customer_id"): wh.append("customers.id = ?"); params.append(args.get("customer_id"))
    if args.get("site_id"): wh.append("sites.id = ?"); params.append(args.get("site_id"))
    if args.get("category"): wh.append("jobs.job_category = ?"); params.append(args.get("category"))
    if args.get("status"): wh.append("jobs.status = ?"); params.append(args.get("status"))
    if args.get("start_after"): wh.append("date(jobs.start_date) >= date(?)"); params.append(args.get("start_after"))
    if args.get("end_before"): wh.append("date(jobs.end_date) <= date(?)"); params.append(args.get("end_before"))
    if args.get("q"):
        like = f"%{args.get('q')}%"
        wh.append("(jobs.description LIKE ? OR jobs.job_number LIKE ? OR sites.name LIKE ? OR customers.name LIKE ?)")
        params += [like, like, like, like]
    if wh: sql += " WHERE " + " AND ".join(wh)
    sql += " ORDER BY date(jobs.start_date) NULLS LAST, jobs.job_number"
    cur.execute(sql, params)
    rows = [dict(r) for r in cur.fetchall()]
    c.close()
    for r in rows:
        for k in ("start_date","end_date","install_date"):
            if r.get(k) and not isinstance(r[k], str): r[k] = str(r[k])
    return jsonify(rows)

@app.patch('/api/jobs/<int:job_id>')
def api_patch_job(job_id):
    data = request.get_json(force=True, silent=False) or {}
    cols, params = [], []
    for k in ("description","job_category","status","start_date","end_date"):
        if k in data:
            cols.append(f"{k} = ?")
            params.append(data[k] if data[k] != "" else None)
    if not cols: return jsonify({"ok": False, "reason":"no fields"}), 400
    params.append(job_id)
    c=db();cur=c.cursor(); cur.execute(f"UPDATE jobs SET {', '.join(cols)} WHERE id=?", params)
    c.commit(); c.close()
    return jsonify({"ok": True, "id": job_id})

@app.get('/api/gantt/global')
def api_gantt_global():
    c=db();cur=c.cursor()
    cur.execute('''SELECT jobs.id, jobs.job_number, jobs.job_category, jobs.status, jobs.start_date, jobs.end_date,
                          sites.name as site_name, sites.id as site_id
                   FROM jobs JOIN sites ON jobs.site_id=sites.id''')
    items=[]
    for r in cur.fetchall():
        r=dict(r)
        if not r['start_date'] or not r['end_date']: continue
        items.append({
            "id": f"job-{r['id']}",
            "name": f"{r['site_name']} • Job {r['job_number']}",
            "start": r['start_date'],
            "end": r['end_date'],
            "progress": 100 if r['status']=='Done' else 50 if r['status']=='In Progress' else 0,
            "custom_class": f"cat-{(r['job_category'] or '').lower()}",
            "meta": {"job_id": r['id'], "site_id": r['site_id'], "site_name": r['site_name']}
        })
    c.close()
    colors={"Drilling":"#b8860b","Electrical":"#b8860b","Domestic":"#b8860b","Ag":"#b8860b", None:"#8a8a8a"}
    return jsonify({"level":"global","items":items,"colors":colors})

@app.get('/api/gantt/site/<int:site_id>')
def api_gantt_site(site_id):
    c=db();cur=c.cursor()
    cur.execute('SELECT name FROM sites WHERE id=?',(site_id,)); site=cur.fetchone()
    if not site: c.close(); abort(404)
    cur.execute('''SELECT id, job_number, job_category, status, start_date, end_date
                   FROM jobs WHERE site_id=? ORDER BY job_number''', (site_id,))
    items=[]
    for r in cur.fetchall():
        r=dict(r)
        if not r['start_date'] or not r['end_date']: continue
        items.append({
            "id": f"job-{r['id']}",
            "name": f"Job {r['job_number']}",
            "start": r['start_date'],
            "end": r['end_date'],
            "progress": 100 if r['status']=='Done' else 50 if r['status']=='In Progress' else 0,
            "custom_class": f"cat-{(r['job_category'] or '').lower()}"
        })
    c.close()
    colors={"Drilling":"#b8860b","Electrical":"#b8860b","Domestic":"#b8860b","Ag":"#b8860b", None:"#8a8a8a"}
    return jsonify({"level":"site","site":{"id":site_id,"name":site['name']},"items":items,"colors":colors})

@app.get('/api/gantt/job/<int:job_id>')
def api_gantt_job(job_id):
    import re
    c=db();cur=c.cursor()
    cur.execute('SELECT * FROM jobs WHERE id=?',(job_id,)); job=cur.fetchone()
    if not job: c.close(); abort(404)
    cur.execute('SELECT content FROM job_notes WHERE job_id=? ORDER BY datetime(created_at) ASC',(job_id,))
    lines=[r['content'] for r in cur.fetchall()]
    items=[]
    line_csv = re.compile(r"^\s*([^,]+)\s*,\s*(\d{4}-\d{2}-\d{2})\s*,\s*(\d{4}-\d{2}-\d{2})(?:\s*,\s*(.+))?\s*$")
    line_dots = re.compile(r"^\s*(\d{4}-\d{2}-\d{2})\s*\.\.\s*(\d{4}-\d{2}-\d{2})\s+(.+?)(?:\s*\(([^)]+)\))?\s*$")
    i=0
    for raw in lines:
        for line in raw.splitlines():
            line=line.strip()
            if not line: continue
            m=line_csv.match(line)
            if m:
                title, s, e, status = m.groups()
                items.append({"id":f"duty-{i}","name":title.strip(),"start":s,"end":e,"progress":100 if (status or '')=='Done' else 50 if (status or '')=='In Progress' else 0,"custom_class":"task"}); i+=1
                continue
            m=line_dots.match(line)
            if m:
                s,e,title,status=m.groups()
                items.append({"id":f"duty-{i}","name":title.strip(),"start":s,"end":e,"progress":100 if (status or '')=='Done' else 50 if (status or '')=='In Progress' else 0,"custom_class":"task"}); i+=1
                continue
            items.append({"id":f"duty-{i}","name":line,"progress":0,"custom_class":"task"}); i+=1
    # If still empty, try parsing jobs.description for CSV-like lines
    if not items and job['description']:
        for line in (job['description'] or '').splitlines():
            line=line.strip()
            m = line_csv.match(line) or line_dots.match(line)
            if m:
                if len(m.groups())==4:
                    title,s,e,status=m.groups()
                else:
                    s,e,title,status=m.groups()
                items.append({"id":f"duty-{i}","name":title.strip(),"start":s,"end":e,"progress":100 if (status or '')=='Done' else 50 if (status or '')=='In Progress' else 0,"custom_class":"task"}); i+=1
    c.close()
    colors={"Drilling":"#b8860b","Electrical":"#b8860b","Domestic":"#b8860b","Ag":"#b8860b", None:"#8a8a8a"}
    return jsonify({"level":"job","job":{"id":job['id'],"number":job['job_number'],"title":job['description'],"category":job['job_category'],"site_id":job['site_id']},"items":items,"colors":colors})

# CSV exports
@app.get('/api/export/jobs.csv')
def export_jobs_csv():
    rows = api_jobs().json
    buf = io.StringIO()
    fieldnames = list(rows[0].keys()) if rows else ["id"]
    w = csv.DictWriter(buf, fieldnames=fieldnames); w.writeheader()
    for r in rows: w.writerow(r)
    return Response(buf.getvalue(), mimetype="text/csv",
                    headers={"Content-Disposition":"attachment; filename=wellatlas_jobs.csv"})

@app.get('/api/export/job/<int:job_id>/tasks.csv')
def export_tasks_csv(job_id):
    data = api_gantt_job(job_id).json
    items = data.get("items", [])
    buf = io.StringIO()
    fieldnames = ["id","name","start","end","progress"]
    w = csv.DictWriter(buf, fieldnames=fieldnames); w.writeheader()
    for d in items: w.writerow({k: d.get(k) for k in fieldnames})
    return Response(buf.getvalue(), mimetype="text/csv",
                    headers={"Content-Disposition":f"attachment; filename=job_{job_id}_tasks.csv"})

@app.get('/healthz')
def healthz(): return 'ok'
