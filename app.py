import os
import sqlite3
from flask import Flask, render_template, g
from datetime import date as _date

app = Flask(__name__)

DB_PATH = os.path.join(os.path.dirname(__file__), "wellatlas_v4_1.db")


def get_db():
    if "db" not in g:
        g.db = sqlite3.connect(DB_PATH)
        g.db.row_factory = sqlite3.Row
    return g.db


@app.teardown_appcontext
def close_db(error):
    db = g.pop("db", None)
    if db is not None:
        db.close()


# -----------------------------
# Homepage (map + today's jobs)
# -----------------------------
@app.route("/")
def home():
    db = get_db()
    cur = db.cursor()

    # get pins
    cur.execute("""
        SELECT id, site_name, lat, lng
        FROM sites
        WHERE lat IS NOT NULL AND lng IS NOT NULL
    """)
    pins = [dict(row) for row in cur.fetchall()]

    # get today's jobs
    today = _date.today().isoformat()
    cur.execute("""
        SELECT j.id, j.title, s.site_name
        FROM jobs j
        JOIN sites s ON j.site_id = s.id
        WHERE j.start_date = ?
        ORDER BY j.start_date
    """, (today,))
    jobs_today = cur.fetchall()

    return render_template(
        "index.html",
        pins=pins,
        jobs_today=jobs_today
    )


# -----------------------------
# Customers list
# -----------------------------
@app.route("/customers")
def customers():
    db = get_db()
    cur = db.cursor()

    cur.execute("SELECT * FROM customers ORDER BY name ASC")
    customers = cur.fetchall()

    return render_template("customers.html", customers=customers)


# -----------------------------
# Customer detail
# -----------------------------
@app.route("/customer/<int:customer_id>")
def customer_detail(customer_id):
    db = get_db()
    cur = db.cursor()

    cur.execute("SELECT * FROM customers WHERE id=?", (customer_id,))
    customer = cur.fetchone()

    # customer’s sites
    cur.execute("SELECT * FROM sites WHERE customer_id=?", (customer_id,))
    sites = cur.fetchall()

    return render_template(
        "customer_detail.html",
        customer=customer,
        sites=sites
    )


# -----------------------------
# Site detail
# -----------------------------
@app.route("/sites/<int:site_id>")
def site_detail(site_id):
    db = get_db()
    cur = db.cursor()

    cur.execute("SELECT * FROM sites WHERE id=?", (site_id,))
    site = cur.fetchone()

    cur.execute("SELECT * FROM jobs WHERE site_id=? ORDER BY start_date", (site_id,))
    jobs = cur.fetchall()

    return render_template(
        "site_detail.html",
        site=site,
        jobs=jobs
    )


# -----------------------------
# Job detail
# -----------------------------
@app.route("/job/<int:job_id>")
def job_detail(job_id):
    db = get_db()
    cur = db.cursor()

    cur.execute("""
        SELECT j.*, s.site_name, c.name AS customer_name
        FROM jobs j
        JOIN sites s ON j.site_id = s.id
        JOIN customers c ON s.customer_id = c.id
        WHERE j.id=?
    """, (job_id,))

    job = cur.fetchone()

    return render_template("job_detail.html", job=job)


# -----------------------------
# Calendar view
# -----------------------------
@app.route("/calendar")
def calendar_view():
    db = get_db()
    cur = db.cursor()

    cur.execute("""
        SELECT j.*, s.site_name
        FROM jobs j
        JOIN sites s ON j.site_id = s.id
        ORDER BY start_date
    """)

    jobs = cur.fetchall()

    return render_template("calendar.html", jobs=jobs)


if __name__ == "__main__":
    app.run(debug=True)

