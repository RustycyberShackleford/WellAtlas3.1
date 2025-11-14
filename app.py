import os
import sqlite3
from datetime import date as _date
from flask import Flask, render_template, request, redirect, url_for, flash, g

# ----------------------------------------
# DATABASE PATH
# ----------------------------------------
DB_PATH = os.path.join(os.path.dirname(__file__), "wellatlas_v4_1.db")

def get_db():
    if "db" not in g:
        g.db = sqlite3.connect(DB_PATH)
        g.db.row_factory = sqlite3.Row
    return g.db

def close_db(e=None):
    db = g.pop("db", None)
    if db is not None:
        db.close()

# ----------------------------------------
# FLASK APP
# ----------------------------------------
app = Flask(__name__)
app.secret_key = "supersecretkey"
app.teardown_appcontext(close_db)

# ----------------------------------------
# PAGE: HOME (Customers + Map)
# ----------------------------------------
@app.route("/")
def home():
    conn = get_db()
    cur = conn.cursor()

    # Fetch customers
    cur.execute("SELECT * FROM customers ORDER BY name ASC")
    customers = cur.fetchall()

    # Fetch site pins
    cur.execute("""
        SELECT 
            s.id,
            s.site_name,
            s.lat,
            s.lng
        FROM sites s
        WHERE s.lat IS NOT NULL AND s.lng IS NOT NULL
    """)
    pins = [
        {
            "id": row["id"],
            "site_name": row["site_name"],
            "lat": row["lat"],
            "lng": row["lng"]
        }
        for row in cur.fetchall()
    ]

    return render_template("index.html", customers=customers, pins=pins)

# ----------------------------------------
# PAGE: CUSTOMERS LIST
# ----------------------------------------
@app.route("/customers")
def customers():
    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT * FROM customers ORDER BY name ASC")
    customers = cur.fetchall()
    return render_template("customers.html", customers=customers)

# ----------------------------------------
# PAGE: CUSTOMER DETAIL
# ----------------------------------------
@app.route("/customer/<int:id>")
def customer_detail(id):
    conn = get_db()
    cur = conn.cursor()

    # Customer record
    cur.execute("SELECT * FROM customers WHERE id = ?", (id,))
    customer = cur.fetchone()

    # Customer's sites
    cur.execute("""
        SELECT *
        FROM sites
        WHERE customer_id = ?
        ORDER BY site_name ASC
    """, (id,))
    sites = cur.fetchall()

    return render_template("customer_detail.html", customer=customer, sites=sites)

# ----------------------------------------
# PAGE: SITE DETAIL
# ----------------------------------------
@app.route("/sites/<int:id>")
def site_detail(id):
    conn = get_db()
    cur = conn.cursor()

    # Site data
    cur.execute("SELECT * FROM sites WHERE id = ?", (id,))
    site = cur.fetchone()

    # Jobs for this site
    cur.execute("""
        SELECT *
        FROM jobs
        WHERE site_id = ?
        ORDER BY date DESC
    """, (id,))
    jobs = cur.fetchall()

    return render_template("site_detail.html", site=site, jobs=jobs)

@app.route("/calendar")
def calendar_view():
    db = get_db()
    cur = db.cursor()
    jobs = cur.execute("""
        SELECT j.*, s.site_name, c.name AS customer_name
        FROM jobs j
        JOIN sites s ON j.site_id = s.id
        JOIN customers c ON s.customer_id = c.id
        ORDER BY j.start_date ASC
    """).fetchall()

    return render_template("calendar.html", jobs=jobs)

# ----------------------------------------
# PAGE: JOB DETAIL
# ----------------------------------------
@app.route("/jobs/<int:id>")
def job_detail(id):
    conn = get_db()
    cur = conn.cursor()

    # Job
    cur.execute("SELECT * FROM jobs WHERE id = ?", (id,))
    job = cur.fetchone()

    return render_template("job_detail.html", job=job)

# ----------------------------------------
# RUN (LOCAL ONLY)
# ----------------------------------------
if __name__ == "__main__":
    app.run(debug=True)
