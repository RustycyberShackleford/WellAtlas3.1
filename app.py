import os, sqlite3, re
from flask import Flask, render_template, request, jsonify, abort, Response

BASE_DIR = os.path.dirname(__file__)
DATA_DIR = os.path.join(BASE_DIR, "data")
DB_PATH = os.path.join(DATA_DIR, "wellatlas.db")

app = Flask(__name__)
app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "dev-secret")

def get_db():
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn

@app.get("/healthz")
def health():
    return "ok", 200

@app.get("/")
def home():
    key = os.environ.get("MAPTILER_KEY", "")
    return render_template("index.html", maptiler_key=key)

@app.get("/api/customers")
def api_customers():
    conn = get_db(); cur = conn.cursor()
    cur.execute("SELECT id,name FROM customers ORDER BY name")
    rows = [dict(r) for r in cur.fetchall()]
    conn.close()
    return jsonify(rows)

@app.get("/api/sites")
def api_sites():
    q = (request.args.get("q") or "").strip()
    customer_id = request.args.get("customer_id")
    conn = get_db(); cur = conn.cursor()
    sql = """
      SELECT sites.*, customers.name AS customer
      FROM sites JOIN customers ON customers.id = sites.customer_id
    """
    wh = []
    params = []
    if customer_id:
        wh.append("customers.id = ?")
        params.append(customer_id)
    if q:
        like = f"%{q}%"
        wh.append("(sites.name LIKE ? OR customers.name LIKE ? OR sites.description LIKE ?)")
        params += [like, like, like]
    if wh:
        sql += " WHERE " + " AND ".join(wh)
    sql += " ORDER BY customers.name, sites.name"
    cur.execute(sql, params)
    rows = [dict(r) for r in cur.fetchall()]
    conn.close()
    return jsonify(rows)

@app.get("/gantt")
def gantt_global():
    return render_template("gantt.html", mode="global")

@app.get("/gantt/site/<int:site_id>")
def gantt_site_page(site_id):
    return render_template("gantt.html", mode="site", site_id=site_id)

@app.get("/gantt/job/<int:job_id>")
def gantt_job_page(job_id):
    return render_template("gantt.html", mode="job", job_id=job_id)

@app.get("/api/jobs_timeline")
def api_jobs_timeline():
    conn = get_db(); cur = conn.cursor()
    cur.execute(
        """
        SELECT customers.name AS customer, sites.name AS site,
               jobs.id AS job_id, jobs.site_id AS site_id,
               jobs.job_number, jobs.job_category AS category,
               jobs.start_date AS start, jobs.end_date AS end
        FROM jobs
        JOIN sites ON sites.id = jobs.site_id
        JOIN customers ON customers.id = sites.customer_id
        WHERE jobs.start_date IS NOT NULL AND jobs.end_date IS NOT NULL
        ORDER BY date(jobs.start_date)
        """
    )
    rows = [dict(r) for r in cur.fetchall()]
    conn.close()
    for r in rows:
        if not isinstance(r["start"], str):
            r["start"] = str(r["start"])
        if not isinstance(r["end"], str):
            r["end"] = str(r["end"])
    return jsonify(rows)

@app.get("/api/gantt/site/<int:site_id>")
def api_gantt_site(site_id):
    conn = get_db(); cur = conn.cursor()
    cur.execute("SELECT id,name FROM sites WHERE id=?", (site_id,))
    site = cur.fetchone()
    if not site:
        conn.close()
        abort(404)
    cur.execute(
        """
        SELECT id AS job_id, job_number, job_category AS category,
               start_date AS start, end_date AS end
        FROM jobs
        WHERE site_id=? AND start_date IS NOT NULL AND end_date IS NOT NULL
        ORDER BY date(start_date)
        """,
        (site_id,)
    )
    items = [dict(r) for r in cur.fetchall()]
    conn.close()
    for r in items:
        if not isinstance(r["start"], str):
            r["start"] = str(r["start"])
        if not isinstance(r["end"], str):
            r["end"] = str(r["end"])
    return jsonify({"site": {"id": site["id"], "name": site["name"]}, "items": items})

@app.get("/api/gantt/job/<int:job_id>")
def api_gantt_job(job_id):
    conn = get_db(); cur = conn.cursor()
    cur.execute("SELECT * FROM jobs WHERE id=?", (job_id,))
    job = cur.fetchone()
    if not job:
        conn.close()
        abort(404)
    cur.execute(
        "SELECT content FROM job_notes WHERE job_id=? ORDER BY datetime(created_at) ASC",
        (job_id,)
    )
    items = []
    i = 0
    line_csv = re.compile(
        r"^\s*([^,]+)\s*,\s*(\d{4}-\d{2}-\d{2})\s*,\s*(\d{4}-\d{2}-\d{2})(?:\s*,\s*(.+))?\s*$"
    )
    for row in cur.fetchall():
        for ln in row["content"].splitlines():
            m = line_csv.match(ln.strip())
            if m:
                title, s, e, status = m.groups()
                items.append({
                    "id": f"duty-{i}",
                    "name": title,
                    "start": s,
                    "end": e,
                    "status": status or ""
                })
                i += 1
    conn.close()
    return jsonify({
        "job": {
            "id": job["id"],
            "number": job["job_number"],
            "title": job["description"],
            "category": job["job_category"],
            "site_id": job["site_id"]
        },
        "items": items
    })

@app.get("/calendar")
def calendar_page():
    return render_template("calendar.html")

@app.get("/api/calendar_events")
def api_calendar_events():
    start = request.args.get("start")
    end = request.args.get("end")
    customer_id = request.args.get("customer_id")
    job_category = request.args.get("job_category")
    status = request.args.get("status")
    conn = get_db(); cur = conn.cursor()
    sql = """
      SELECT jobs.id, jobs.job_number, jobs.job_category, jobs.status,
             jobs.start_date, jobs.end_date,
             sites.id AS site_id, sites.name AS site,
             customers.id AS customer_id, customers.name AS customer
      FROM jobs
      JOIN sites ON sites.id = jobs.site_id
      JOIN customers ON customers.id = sites.customer_id
      WHERE jobs.start_date IS NOT NULL AND jobs.end_date IS NOT NULL
    """
    params = []
    if start:
        sql += " AND date(jobs.end_date) >= date(?)"
        params.append(start)
    if end:
        sql += " AND date(jobs.start_date) <= date(?)"
        params.append(end)
    if customer_id:
        sql += " AND customers.id = ?"
        params.append(customer_id)
    if job_category:
        sql += " AND jobs.job_category = ?"
        params.append(job_category)
    if status:
        sql += " AND jobs.status = ?"
        params.append(status)
    sql += " ORDER BY date(jobs.start_date)"
    cur.execute(sql, params)
    rows = [dict(r) for r in cur.fetchall()]
    conn.close()
    events = []
    for r in rows:
        events.append({
            "id": r["id"],
            "title": f"{r['job_number']} — {r['site']}",
            "start": r["start_date"],
            "end": r["end_date"] or r["start_date"],
            "category": r["job_category"],
            "status": r["status"],
            "customer": r["customer"],
            "site": r["site"],
            "url": f"/gantt/job/{r['id']}"
        })
    return jsonify(events)

@app.get("/calendar.ics")
def calendar_ics():
    with app.test_request_context("/api/calendar_events", query_string=request.args):
        resp = api_calendar_events()
    data = resp.get_json()
    lines = ["BEGIN:VCALENDAR","VERSION:2.0","PRODID:-//WellAtlas//Calendar//EN"]
    import uuid
    for ev in data:
        uid = uuid.uuid4()
        start = ev["start"].replace("-", "") + "T080000Z"
        end = (ev["end"] or ev["start"]).replace("-", "") + "T170000Z"
        lines += [
            "BEGIN:VEVENT",
            f"UID:{uid}@wellatlas",
            f"SUMMARY:{ev['title']}",
            f"DTSTART:{start}",
            f"DTEND:{end}",
            f"DESCRIPTION:{ev['category']} | {ev['status']} | {ev['customer']}",
            "END:VEVENT"
        ]
    lines.append("END:VCALENDAR")
    ics = "\r\n".join(lines)
    return Response(ics, mimetype="text/calendar")

@app.get("/crew")
def crew_page():
    return render_template("crew.html")

@app.get("/api/crew")
def api_crew_list():
    conn = get_db(); cur = conn.cursor()
    cur.execute("SELECT * FROM crew_members ORDER BY name")
    rows = [dict(r) for r in cur.fetchall()]
    conn.close()
    return jsonify(rows)

@app.post("/api/crew")
def api_crew_create():
    data = request.get_json(force=True)
    name = data.get("name")
    if not name:
        abort(400, "name required")
    role = data.get("role")
    phone = data.get("phone")
    email = data.get("email")
    notes = data.get("notes")
    conn = get_db(); cur = conn.cursor()
    cur.execute(
        "INSERT INTO crew_members(name,role,phone,email,notes) VALUES (?,?,?,?,?)",
        (name, role, phone, email, notes)
    )
    conn.commit()
    new_id = cur.lastrowid
    conn.close()
    return jsonify({"id": new_id}), 201

@app.get("/assign/<int:job_id>")
def assign_page(job_id):
    conn = get_db(); cur = conn.cursor()
    cur.execute(
        """
        SELECT jobs.*, sites.name AS site, customers.name AS customer
        FROM jobs
        JOIN sites ON sites.id = jobs.site_id
        JOIN customers ON customers.id = sites.customer_id
        WHERE jobs.id = ?
        """,
        (job_id,)
    )
    job = cur.fetchone()
    conn.close()
    if not job:
        abort(404)
    return render_template("assign.html", job=job)

@app.post("/api/assign/<int:job_id>")
def api_assign_create(job_id):
    data = request.get_json(force=True)
    crew_id = data.get("crew_id")
    start = data.get("start_date")
    end = data.get("end_date")
    role = data.get("role")
    if not crew_id or not start or not end:
        abort(400, "crew_id, start_date, end_date required")
    conn = get_db(); cur = conn.cursor()
    cur.execute("SELECT id FROM jobs WHERE id=?", (job_id,))
    if not cur.fetchone():
        conn.close()
        abort(404, "job not found")
    cur.execute("SELECT id FROM crew_members WHERE id=?", (crew_id,))
    if not cur.fetchone():
        conn.close()
        abort(400, "crew not found")
    cur.execute(
        "INSERT INTO job_assignments(job_id,crew_id,start_date,end_date,role) VALUES (?,?,?,?,?)",
        (job_id, crew_id, start, end, role)
    )
    conn.commit()
    conn.close()
    return jsonify({"ok": True}), 201

@app.get("/calendar/resources")
def calendar_resources_page():
    return render_template("calendar_resources.html")

@app.get("/api/calendar_assignments")
def api_calendar_assignments():
    start = request.args.get("start")
    end = request.args.get("end")
    crew_id = request.args.get("crew_id")
    customer_id = request.args.get("customer_id")
    job_category = request.args.get("job_category")
    status = request.args.get("status")
    conn = get_db(); cur = conn.cursor()
    sql = """
      SELECT ja.id, ja.start_date, ja.end_date,
             cm.name AS crew, cm.id AS crew_id,
             j.id AS job_id, j.job_number, j.job_category, j.status,
             s.id AS site_id, s.name AS site,
             c.id AS customer_id, c.name AS customer
      FROM job_assignments ja
      JOIN crew_members cm ON cm.id = ja.crew_id
      JOIN jobs j ON j.id = ja.job_id
      JOIN sites s ON s.id = j.site_id
      JOIN customers c ON c.id = s.customer_id
      WHERE ja.start_date IS NOT NULL AND ja.end_date IS NOT NULL
    """
    params = []
    if start:
        sql += " AND date(ja.end_date) >= date(?)"
        params.append(start)
    if end:
        sql += " AND date(ja.start_date) <= date(?)"
        params.append(end)
    if crew_id:
        sql += " AND cm.id = ?"
        params.append(crew_id)
    if customer_id:
        sql += " AND c.id = ?"
        params.append(customer_id)
    if job_category:
        sql += " AND j.job_category = ?"
        params.append(job_category)
    if status:
        sql += " AND j.status = ?"
        params.append(status)
    sql += " ORDER BY date(ja.start_date)"
    cur.execute(sql, params)
    rows = [dict(r) for r in cur.fetchall()]
    conn.close()
    items = []
    for r in rows:
        items.append({
            "id": r["id"],
            "crew": r["crew"],
            "crew_id": r["crew_id"],
            "job_id": r["job_id"],
            "job_number": r["job_number"],
            "category": r["job_category"],
            "status": r["status"],
            "site": r["site"],
            "customer": r["customer"],
            "start": r["start_date"],
            "end": r["end_date"],
            "url": f"/gantt/job/{r['job_id']}"
        })
    return jsonify(items)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 8000)), debug=True)
