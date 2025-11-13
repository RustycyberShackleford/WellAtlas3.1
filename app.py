import os
import sqlite3
from datetime import datetime, date
from flask import Flask, render_template, request, redirect, url_for, send_from_directory, abort, flash

# -------------------------------------------------
# Flask App Setup
# -------------------------------------------------
app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "wellatlas-dev-key")

DB_PATH = os.path.join(os.path.dirname(__file__), "wellatlas_v4_demo.db")
UPLOAD_ROOT = os.path.join("static", "uploads", "jobs")  # static/uploads/jobs/<job_id>/
os.makedirs(UPLOAD_ROOT, exist_ok=True)

MAPTILER_KEY = os.environ.get("MAPTILER_KEY", "YOUR_MAPTILER_KEY_HERE")


# -------------------------------------------------
# DB Helpers
# -------------------------------------------------
def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_db()
    cur = conn.cursor()

    # Customers
    cur.execute("""
        CREATE TABLE IF NOT EXISTS customers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            notes TEXT
        )
    """)

    # Sites
    cur.execute("""
        CREATE TABLE IF NOT EXISTS sites (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            customer_id INTEGER,
            site_name TEXT NOT NULL,
            street TEXT,
            city TEXT,
            state TEXT,
            zip TEXT,
            contact_name TEXT,
            phone TEXT,
            email TEXT,
            notes TEXT,
            lat REAL,
            lng REAL
        )
    """)

    # Jobs
    cur.execute("""
        CREATE TABLE IF NOT EXISTS jobs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            site_id INTEGER NOT NULL,
            job_number TEXT,
            title TEXT,
            division TEXT,
            status TEXT,
            description TEXT,
            start_date TEXT,
            end_date TEXT
        )
    """)

    # Job Files (attachments)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS job_files (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            job_id INTEGER NOT NULL,
            filename TEXT NOT NULL,
            filetype TEXT NOT NULL,
            url TEXT NOT NULL
        )
    """)

    # Job Notes
    cur.execute("""
        CREATE TABLE IF NOT EXISTS job_notes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            job_id INTEGER NOT NULL,
            text TEXT NOT NULL,
            timestamp TEXT NOT NULL
        )
    """)

    conn.commit()
    conn.close()


# -------------------------------------------------
# Utility Functions
# -------------------------------------------------
def parse_date(s):
    if not s:
        return None
    try:
        return datetime.strptime(s, "%Y-%m-%d").date()
    except ValueError:
        return None


def calc_duration(start_s, end_s):
    sd = parse_date(start_s)
    ed = parse_date(end_s)
    if not sd or not ed:
        return 0
    return (ed - sd).days + 1


def is_overdue(end_s, status):
    ed = parse_date(end_s)
    if not ed:
        return False
    if status is None:
        status = ""
    today = date.today()
    return ed < today and status.lower() not in ("complete", "completed", "done")


def filetype_from_name(fn):
    lower = fn.lower()
    if lower.endswith(".pdf"):
        return "pdf"
    if lower.endswith((".jpg", ".jpeg", ".png", ".gif", ".webp")):
        return "image"
    if lower.endswith((".mp4", ".mov", ".avi", ".mkv")):
        return "video"
    return "other"


# -------------------------------------------------
# Home / Map
# -------------------------------------------------
@app.route("/")
def home():
    conn = get_db()
    cur = conn.cursor()
    cur.execute("""
        SELECT s.id, s.site_name, s.street, s.city, s.state, s.zip, s.lat, s.lng
        FROM sites s
        WHERE s.lat IS NOT NULL AND s.lng IS NOT NULL
    """)
    rows = cur.fetchall()
    conn.close()

    sites = []
    for r in rows:
        sites.append({
            "id": r["id"],
            "site_name": r["site_name"],
            "street": r["street"] or "",
            "city": r["city"] or "",
            "state": r["state"] or "",
            "zip": r["zip"] or "",
            "lat": r["lat"],
            "lng": r["lng"],
        })

    return render_template("index.html", sites=sites, maptiler_key=MAPTILER_KEY)


# -------------------------------------------------
# Customers
# -------------------------------------------------
@app.route("/customers")
def customers():
    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT id, name, notes FROM customers ORDER BY name")
    custs = cur.fetchall()
    conn.close()
    return render_template("customers.html", customers=custs)


@app.route("/customer/<int:customer_id>")
def customer_detail(customer_id):
    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT * FROM customers WHERE id = ?", (customer_id,))
    customer = cur.fetchone()
    if not customer:
        conn.close()
        abort(404)

    cur.execute("""
        SELECT * FROM sites
        WHERE customer_id = ?
        ORDER BY site_name
    """, (customer_id,))
    sites = cur.fetchall()
    conn.close()
    return render_template("customer_detail.html", customer=customer, sites=sites)


@app.route("/new_customer", methods=["GET", "POST"])
def new_customer():
    if request.method == "POST":
        name = request.form.get("name")
        notes = request.form.get("notes")
        if not name:
            flash("Customer name is required.")
            return redirect(url_for("new_customer"))
        conn = get_db()
        cur = conn.cursor()
        cur.execute("INSERT INTO customers (name, notes) VALUES (?, ?)", (name, notes))
        conn.commit()
        conn.close()
        return redirect(url_for("customers"))
    return render_template("new_customer.html")


# -------------------------------------------------
# Sites
# -------------------------------------------------
@app.route("/site/<int:site_id>")
def site_detail(site_id):
    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT * FROM sites WHERE id = ?", (site_id,))
    site = cur.fetchone()
    if not site:
        conn.close()
        abort(404)

    # Jobs at this site
    cur.execute("""
        SELECT * FROM jobs
        WHERE site_id = ?
        ORDER BY 
            CASE WHEN start_date IS NULL THEN 1 ELSE 0 END,
            start_date ASC
    """, (site_id,))
    job_rows = cur.fetchall()
    conn.close()

    jobs = []
    for j in job_rows:
        sd = j["start_date"]
        ed = j["end_date"]
        jobs.append({
            "id": j["id"],
            "job_number": j["job_number"],
            "title": j["title"],
            "division": j["division"],
            "status": j["status"] or "",
            "start_date": sd or "No start",
            "end_date": ed or "No end",
            "duration": calc_duration(sd, ed),
            "is_overdue": is_overdue(ed, j["status"] or "")
        })

    return render_template(
        "site_detail.html",
        site=site,
        jobs=jobs,
        maptiler_key=MAPTILER_KEY
    )


@app.route("/edit_site/<int:site_id>", methods=["GET", "POST"])
def edit_site(site_id):
    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT * FROM sites WHERE id = ?", (site_id,))
    site = cur.fetchone()
    if not site:
        conn.close()
        abort(404)

    if request.method == "POST":
        site_name = request.form.get("site_name")
        street = request.form.get("street")
        city = request.form.get("city")
        state = request.form.get("state")
        zip_code = request.form.get("zip")
        contact_name = request.form.get("contact_name")
        phone = request.form.get("phone")
        email = request.form.get("email")
        notes = request.form.get("notes")

        cur.execute("""
            UPDATE sites
            SET site_name = ?, street = ?, city = ?, state = ?, zip = ?,
                contact_name = ?, phone = ?, email = ?, notes = ?
            WHERE id = ?
        """, (site_name, street, city, state, zip_code, contact_name, phone, email, notes, site_id))
        conn.commit()
        conn.close()
        return redirect(url_for("site_detail", site_id=site_id))

    conn.close()
    return render_template("edit_site.html", site=site)


@app.route("/add_site", methods=["POST"])
def add_site():
    site_name = request.form.get("site_name")
    street = request.form.get("street")
    city = request.form.get("city")
    state = request.form.get("state")
    zip_code = request.form.get("zip")
    contact_name = request.form.get("contact_name")
    phone = request.form.get("phone")
    email = request.form.get("email")
    notes = request.form.get("notes")
    lat = request.form.get("lat")
    lng = request.form.get("lng")

    if not site_name:
        flash("Site name is required.")
        return redirect(url_for("home"))

    try:
        lat_val = float(lat) if lat else None
        lng_val = float(lng) if lng else None
    except ValueError:
        lat_val = None
        lng_val = None

    conn = get_db()
    cur = conn.cursor()
    # For now no forced customer_id; you can wire it later
    cur.execute("""
        INSERT INTO sites (customer_id, site_name, street, city, state, zip,
                           contact_name, phone, email, notes, lat, lng)
        VALUES (NULL, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (site_name, street, city, state, zip_code,
          contact_name, phone, email, notes, lat_val, lng_val))
    conn.commit()
    conn.close()

    return redirect(url_for("home"))


# -------------------------------------------------
# Jobs
# -------------------------------------------------
@app.route("/job/<int:job_id>")
def job_detail(job_id):
    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT * FROM jobs WHERE id = ?", (job_id,))
    job = cur.fetchone()
    if not job:
        conn.close()
        abort(404)

    cur.execute("""
        SELECT * FROM sites
        WHERE id = ?
    """, (job["site_id"],))
    site = cur.fetchone()
    if not site:
        conn.close()
        abort(404)

    # Attachments
    cur.execute("SELECT * FROM job_files WHERE job_id = ?", (job_id,))
    files_rows = cur.fetchall()

    files = []
    for f in files_rows:
        files.append({
            "id": f["id"],
            "filename": f["filename"],
            "type": f["filetype"],
            "url": f["url"]
        })

    # Notes
    cur.execute("SELECT * FROM job_notes WHERE job_id = ? ORDER BY id DESC", (job_id,))
    notes_rows = cur.fetchall()
    notes = []
    for n in notes_rows:
        notes.append({
            "id": n["id"],
            "text": n["text"],
            "timestamp": n["timestamp"]
        })

    conn.close()

    sd = job["start_date"]
    ed = job["end_date"]

    job_enriched = {
        "id": job["id"],
        "job_number": job["job_number"],
        "title": job["title"],
        "division": job["division"],
        "status": job["status"] or "",
        "description": job["description"],
        "start_date": sd or "",
        "end_date": ed or "",
        "duration": calc_duration(sd, ed)
    }

    return render_template(
        "job_detail.html",
        job=job_enriched,
        site=site,
        files=files,
        notes=notes,
        maptiler_key=MAPTILER_KEY
    )


@app.route("/add_job", methods=["GET", "POST"])
def add_job():
    conn = get_db()
    cur = conn.cursor()
    # Let user choose site from list
    cur.execute("SELECT id, site_name FROM sites ORDER BY site_name")
    sites = cur.fetchall()

    if request.method == "POST":
        site_id = request.form.get("site_id")
        job_number = request.form.get("job_number")
        title = request.form.get("title")
        division = request.form.get("division")
        status = request.form.get("status")
        description = request.form.get("description")
        start_date = request.form.get("start_date")
        end_date = request.form.get("end_date")

        cur.execute("""
            INSERT INTO jobs (site_id, job_number, title, division, status, description, start_date, end_date)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (site_id, job_number, title, division, status, description, start_date, end_date))
        conn.commit()
        conn.close()
        return redirect(url_for("home"))

    conn.close()
    return render_template("add_job.html", sites=sites)


@app.route("/add_job/site/<int:site_id>", methods=["GET", "POST"])
def add_job_with_site(site_id):
    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT id, site_name FROM sites WHERE id = ?", (site_id,))
    site = cur.fetchone()
    if not site:
        conn.close()
        abort(404)

    if request.method == "POST":
        job_number = request.form.get("job_number")
        title = request.form.get("title")
        division = request.form.get("division")
        status = request.form.get("status")
        description = request.form.get("description")
        start_date = request.form.get("start_date")
        end_date = request.form.get("end_date")

        cur.execute("""
            INSERT INTO jobs (site_id, job_number, title, division, status, description, start_date, end_date)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (site_id, job_number, title, division, status, description, start_date, end_date))
        conn.commit()
        conn.close()
        return redirect(url_for("site_detail", site_id=site_id))

    conn.close()
    return render_template("add_job.html", sites=[site])


@app.route("/edit_job/<int:job_id>", methods=["GET", "POST"])
def edit_job(job_id):
    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT * FROM jobs WHERE id = ?", (job_id,))
    job = cur.fetchone()
    if not job:
        conn.close()
        abort(404)

    if request.method == "POST":
        job_number = request.form.get("job_number")
        title = request.form.get("title")
        division = request.form.get("division")
        status = request.form.get("status")
        description = request.form.get("description")
        start_date = request.form.get("start_date")
        end_date = request.form.get("end_date")

        cur.execute("""
            UPDATE jobs
            SET job_number = ?, title = ?, division = ?, status = ?,
                description = ?, start_date = ?, end_date = ?
            WHERE id = ?
        """, (job_number, title, division, status, description, start_date, end_date, job_id))
        conn.commit()
        conn.close()
        return redirect(url_for("job_detail", job_id=job_id))

    conn.close()
    return render_template("edit_job.html", job=job)


# -------------------------------------------------
# Job File Uploads
# -------------------------------------------------
@app.route("/job/<int:job_id>/upload", methods=["POST"])
def upload_job_file(job_id):
    file = request.files.get("file")
    if not file or file.filename == "":
        flash("No file selected.")
        return redirect(url_for("job_detail", job_id=job_id))

    filename = file.filename
    jdir = os.path.join(UPLOAD_ROOT, str(job_id))
    os.makedirs(jdir, exist_ok=True)
    save_path = os.path.join(jdir, filename)
    file.save(save_path)

    filetype = filetype_from_name(filename)
    # Build URL
    rel_path = os.path.join("uploads", "jobs", str(job_id), filename)
    url = url_for("static", filename=rel_path)

    conn = get_db()
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO job_files (job_id, filename, filetype, url)
        VALUES (?, ?, ?, ?)
    """, (job_id, filename, filetype, url))
    conn.commit()
    conn.close()

    return redirect(url_for("job_detail", job_id=job_id))


# -------------------------------------------------
# Job Notes
# -------------------------------------------------
@app.route("/job/<int:job_id>/note", methods=["POST"])
def add_job_note(job_id):
    note = request.form.get("note")
    if not note:
        return redirect(url_for("job_detail", job_id=job_id))

    ts = datetime.now().strftime("%Y-%m-%d %H:%M")
    conn = get_db()
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO job_notes (job_id, text, timestamp)
        VALUES (?, ?, ?)
    """, (job_id, note, ts))
    conn.commit()
    conn.close()

    return redirect(url_for("job_detail", job_id=job_id))


# -------------------------------------------------
# Calendar
# -------------------------------------------------
@app.route("/calendar")
def calendar_view():
    conn = get_db()
    cur = conn.cursor()
    # join jobs with sites
    cur.execute("""
        SELECT j.id, j.job_number, j.title, j.start_date, j.end_date,
               j.division, j.status
        FROM jobs j
        ORDER BY j.start_date
    """)
    rows = cur.fetchall()
    conn.close()

    events = []
    for r in rows:
        if not r["start_date"]:
            continue
        events.append({
            "id": r["id"],
            "title": f"{r['job_number']} – {r['title']}",
            "start": r["start_date"],
            "end": r["end_date"] if r["end_date"] else r["start_date"],
            "division": r["division"] or "",
            "status": r["status"] or "",
            "url": url_for("job_detail", job_id=r["id"])
        })

    return render_template("calendar.html", events=events)


# -------------------------------------------------
# Global Gantt Placeholder
# -------------------------------------------------
@app.route("/gantt")
def gantt_global():
    # You can expand this later to aggregate all jobs
    conn = get_db()
    cur = conn.cursor()
    cur.execute("""
        SELECT j.id, j.job_number, j.title, j.start_date, j.end_date,
               s.site_name
        FROM jobs j
        JOIN sites s ON j.site_id = s.id
        ORDER BY j.start_date
    """)
    rows = cur.fetchall()
    conn.close()

    tasks = []
    for r in rows:
        if not r["start_date"] or not r["end_date"]:
            continue
        tasks.append({
            "id": r["id"],
            "name": f"{r['job_number']} – {r['title']} ({r['site_name']})",
            "start": r["start_date"],
            "end": r["end_date"],
        })

    return render_template("gantt.html", tasks=tasks)


# -------------------------------------------------
# Settings Placeholder
# -------------------------------------------------
@app.route("/settings")
def settings():
    return render_template("settings.html", maptiler_key=MAPTILER_KEY)


# -------------------------------------------------
# App Entry
# -------------------------------------------------
if __name__ == "__main__":
    init_db()
    app.run(debug=True)
