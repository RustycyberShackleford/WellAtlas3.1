
import os, re, sqlite3
from flask import Flask, render_template, request, jsonify, abort
BASE_DIR = os.path.dirname(__file__); DATA_DIR = os.path.join(BASE_DIR, "data"); DB_PATH=os.path.join(DATA_DIR,"wellatlas.db")
app=Flask(__name__); app.config["SECRET_KEY"]=os.environ.get("SECRET_KEY","dev-secret")
def db(): c=sqlite3.connect(DB_PATH,check_same_thread=False); c.row_factory=sqlite3.Row; return c

@app.get('/')
def home():
    key = os.environ.get('MAPTILER_KEY','')
    return render_template('index.html', maptiler_key=key)

@app.get('/gantt')
def gantt_page(): return render_template('gantt.html', mode='global')

@app.get('/gantt/site/<int:site_id>')
def gantt_site_page(site_id): return render_template('gantt.html', mode='site', site_id=site_id)

@app.get('/gantt/job/<int:job_id>')
def gantt_job_page(job_id): return render_template('gantt.html', mode='job', job_id=job_id)

@app.get('/api/jobs_timeline')
def api_jobs_timeline():
    c=db();cur=c.cursor()
    cur.execute('''SELECT customers.name customer, sites.name site, jobs.id job_id, jobs.site_id site_id, jobs.job_number job_number, jobs.job_category category, jobs.start_date start, jobs.end_date end
                   FROM jobs JOIN sites ON jobs.site_id=sites.id JOIN customers ON customers.id=sites.customer_id
                   WHERE jobs.start_date IS NOT NULL AND jobs.end_date IS NOT NULL ORDER BY date(jobs.start_date)''')
    rows=[dict(r) for r in cur.fetchall()]; c.close()
    for r in rows:
        if not isinstance(r['start'], str): r['start']=str(r['start'])
        if not isinstance(r['end'], str): r['end']=str(r['end'])
    return jsonify(rows)

@app.get('/api/gantt/site/<int:site_id>')
def api_gantt_site(site_id):
    c=db();cur=c.cursor(); cur.execute('SELECT id,name FROM sites WHERE id=?',(site_id,)); s=cur.fetchone()
    if not s: c.close(); abort(404)
    cur.execute('SELECT id job_id, job_number, job_category category, start_date start, end_date end FROM jobs WHERE site_id=? AND start_date IS NOT NULL AND end_date IS NOT NULL ORDER BY date(start)',(site_id,))
    rows=[dict(r) for r in cur.fetchall()]; c.close()
    for r in rows:
        if not isinstance(r['start'], str): r['start']=str(r['start'])
        if not isinstance(r['end'], str): r['end']=str(r['end'])
    return jsonify({"site":{"id":s['id'],"name":s['name']},"items":rows})

@app.get('/api/gantt/job/<int:job_id>')
def api_gantt_job(job_id):
    c=db();cur=c.cursor(); cur.execute('SELECT * FROM jobs WHERE id=?',(job_id,)); job=cur.fetchone()
    if not job: c.close(); abort(404)
    cur.execute('SELECT content FROM job_notes WHERE job_id=? ORDER BY datetime(created_at) ASC',(job_id,))
    items=[]; i=0; line_csv=re.compile(r'^\s*([^,]+)\s*,\s*(\d{4}-\d{2}-\d{2})\s*,\s*(\d{4}-\d{2}-\d{2})(?:\s*,\s*(.+))?\s*$')
    for row in cur.fetchall():
        for ln in row['content'].splitlines():
            m=line_csv.match(ln.strip())
            if m:
                title,s,e,status=m.groups(); items.append({"id":f"duty-{i}","name":title,"start":s,"end":e,"status":status or ""}); i+=1
    c.close(); return jsonify({"job":{"id":job['id'],"number":job['job_number'],"title":job['description'],"category":job['job_category'],"site_id":job['site_id']},"items":items})

@app.get('/api/customers')
def api_customers():
    c=db();cur=c.cursor();cur.execute('SELECT id,name FROM customers ORDER BY name'); rows=[dict(r) for r in cur.fetchall()]; c.close(); return jsonify(rows)

@app.get('/api/sites')
def api_sites():
    q=(request.args.get('q') or '').strip(); customer_id=request.args.get('customer_id');
    c=db();cur=c.cursor(); sql='SELECT sites.*, customers.name customer FROM sites JOIN customers ON customers.id=sites.customer_id'; wh=[]; params=[]
    if customer_id: wh.append('customers.id=?'); params.append(customer_id)
    if q: like=f'%{q}%'; wh.append('(sites.name LIKE ? OR customers.name LIKE ? OR sites.description LIKE ?)'); params+= [like,like,like]
    if wh: sql+=' WHERE '+ ' AND '.join(wh)
    sql += ' ORDER BY customers.name, sites.name'
    cur.execute(sql, params); rows=[dict(r) for r in cur.fetchall()]; c.close(); return jsonify(rows)

if __name__=='__main__':
    app.run(host='0.0.0.0', port=int(os.getenv('PORT','8000')), debug=True)
