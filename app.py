from flask import Flask, render_template, request, redirect, url_for, flash
import sqlite3
from datetime import datetime

app = Flask(__name__)
app.secret_key = "supersecretkey"

# Change this if you renamed the file
DATABASE = "wellatlas.db"   # or "wellatlas_v5.db"


def get_db():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn


# -----------------------------
# HOME PAGE
# -----------------------------
@app.route("/")
def home():
    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT * FROM customers ORDER BY name ASC")
    customers = cur.fetchall()
    return render_template("index.html", customers=customers)


# -----------------------------
# CUSTOMERS
# -----------------------------
@app.route("/customers")
def customers():
    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT * FROM customers ORDER BY name ASC")
    customers = cur.fetchall()
    return render_template("customers.html", customers=customers)


@app.route("/customer/<int:id>")
def customer_detail(id):
    conn = get_db()
    cur = conn.cursor()

    cur.execute("SELECT * FROM customers WHERE id = ?", (id,))
    customer = cur.fetchone()

    cur.execute("SELECT * FROM sites WHERE customer_id = ?", (id,))
    sites = cur.fetchall()

    return render_template("customer_detail.html", customer=customer, sites=sites)


@app.route("/new_customer", methods=["GET", "POST"])
def new_customer():
    if request.method == "POST":
        name = request.form["name"]
        phone = request.form["phone"]
        email = request.form["email"]
        notes = request.form["notes"]

        conn = get_db()
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO customers (name, phone, email, notes) VALUES (?, ?, ?, ?)",
            (name, phone, email, notes),
        )
        conn.commit()
        return redirect(url_for("customers"))

    return render_template("new_customer.html")


# -----------------------------
# SITES
# -----------------------------
@app.route("/site/<int:id>")
def site_detail(id):
    conn = get_db()
    cur = conn.cursor()

    cur.execute("SELECT * FROM sites WHERE id = ?", (id,))
    site = cur.fetchone()

    cur.execute("SELECT * FROM jobs WHERE site_id = ?", (id,))
    jobs = cur.fetchall()

    return render_template("site_detail.html", site=site, jobs=jobs)


@app.route("/add_site/<int:customer_id>", methods=["GET", "POST"])
def add_site(customer_id):
    if request.method == "POST":
        name = request.form["name"]
        address = request.form["address"]
        lat = request.form["lat"]
        lng = request.form["lng"]

        conn = get_db()
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO sites (customer_id, name, address, lat, lng) VALUES (?, ?, ?, ?, ?)",
            (customer_id, name, address, lat, lng),
        )
        conn.commit()
        return redirect(url_for("customer_detail", id=customer_id))

    return render_template("add_site.html", customer_id=customer_id)


@app.route("/edit_site/<int:id>", methods=["GET", "POST"])
def edit_site(id):
    conn = get_db()
    cur = conn.cursor()

    cur.execute("SELECT * FROM sites WHERE id = ?", (id,))
    site = cur.fetchone()

    if request.method == "POST":
        name = request.form["name"]
        address = request.form["address"]
        lat = request.form["lat"]
        lng = request.form["lng"]

        cur.execute(
            "UPDATE sites SET name=?, address=?, lat=?, lng=? WHERE id=?",
            (name, address, lat, lng, id),
        )
        conn.commit()
        return redirect(url_for("site_detail", id=id))

    return render_template("edit_site.html", site=site)


# -----------------------------
# JOBS
# -----------------------------
@app.route("/job/<int:id>")
def job_detail(id):
    conn = get_db()
    cur = conn.cursor()

    cur.execute("SELECT * FROM jobs WHERE id = ?", (id,))
    job = cur.fetchone()

    cur.execute("SELECT * FROM job_notes WHERE job_id = ? ORDER BY date ASC", (id,))
    notes = cur.fetchall()

    cur.execute("SELECT * FROM job_files WHERE job_id = ?", (id,))
    files = cur.fetchall()

    return render_template("job_detail.html", job=job, notes=notes, files=files)


@app.route("/add_job/<int:site_id>", methods=["GET", "POST"])
def add_job(site_id):
    if request.method == "POST":
        job_number = request.form["job_number"]
        category = request.form["category"]
        date = request.form["date"]
        description = request.form["description"]

        conn = get_db()
        cur = conn.cursor()

        cur.execute(
            """
            INSERT INTO jobs (site_id, job_number, category, date, description)
            VALUES (?, ?, ?, ?, ?)
            """,
            (site_id, job_number, category, date, description),
        )
        conn.commit()

        return redirect(url_for("site_detail", id=site_id))

    return render_template("add_job.html", site_id=site_id)


@app.route("/edit_job/<int:id>", methods=["GET", "POST"])
def edit_job(id):
    conn = get_db()
    cur = conn.cursor()

    cur.execute("SELECT * FROM jobs WHERE id = ?", (id,))
    job = cur.fetchone()

    if request.method == "POST":
        job_number = request.form["job_number"]
        category = request.form["category"]
        date = request.form["date"]
        description = request.form["description"]

        cur.execute(
            """
            UPDATE jobs
            SET job_number=?, category=?, date=?, description=?
            WHERE id=?
            """,
            (job_number, category, date, description, id),
        )
        conn.commit()

        return redirect(url_for("job_detail", id=id))

    return render_template("edit_job.html", job=job)


# -----------------------------
# CALENDAR
# -----------------------------
@app.route("/calendar")
def calendar_view():
    conn = get_db()
    cur = conn.cursor()

    cur.execute("SELECT * FROM jobs ORDER BY date ASC")
    jobs = cur.fetchall()

    return render_template("calendar.html", jobs=jobs)


# -----------------------------
# SETTINGS PAGE
# -----------------------------
@app.route("/settings")
def settings():
    return render_template("settings.html")


# -----------------------------
# RUN
# -----------------------------
if __name__ == "__main__":
    app.run(debug=True)
