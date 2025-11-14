from flask import Flask, render_template, request, redirect, url_for, flash
import sqlite3
from datetime import datetime

app = Flask(__name__)
app.secret_key = "supersecretkey"

DATABASE = "wellatlas.db"


# -------------------------
# Database Connection
# -------------------------
def get_db():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn


# -------------------------
# HOME (formerly index)
# -------------------------
@app.route("/")
def home():
    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT * FROM customers ORDER BY name ASC")
    customers = cur.fetchall()
    return render_template("index.html", customers=customers)


# -------------------------
# CUSTOMERS LIST
# -------------------------
@app.route("/customers")
def customers():
    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT * FROM customers ORDER BY name ASC")
    customers = cur.fetchall()
    return render_template("customers.html", customers=customers)


# -------------------------
# CUSTOMER DETAIL
# -------------------------
@app.route("/customer/<int:id>")
def customer_detail(id):
    conn = get_db()
    cur = conn.cursor()

    cur.execute("SELECT * FROM customers WHERE id = ?", (id,))
    customer = cur.fetchone()

    cur.execute("SELECT * FROM sites WHERE customer_id = ?", (id,))
    sites = cur.fetchall()

    return render_template("customer_detail.html", customer=customer, sites=sites)


# -------------------------
# SITE DETAIL
# -------------------------
@app.route("/site/<int:id>")
def site_detail(id):
    conn = get_db()
    cur = conn.cursor()

    cur.execute("SELECT * FROM sites WHERE id = ?", (id,))
    site = cur.fetchone()

    cur.execute("SELECT * FROM jobs WHERE site_id = ?", (id,))
    jobs = cur.fetchall()

    return render_template("site_detail.html", site=site, jobs=jobs)


# -------------------------
# JOB DETAIL
# -------------------------
@app.route("/job/<int:id>")
def job_detail(id):
    conn = get_db()
    cur = conn.cursor()

    cur.execute("SELECT * FROM jobs WHERE id = ?", (id,))
    job = cur.fetchone()

    return render_template("job_detail.html", job=job)


# -------------------------
# ADD SITE
# -------------------------
@app.route("/add_site", methods=["GET", "POST"])
def add_site():
    conn = get_db()
    cur = conn.cursor()

    if request.method == "POST":
        customer_id = request.form["customer_id"]
        site_name = request.form["site_name"]
        street = request.form["street"]
        city = request.form["city"]
        state = request.form["state"]
        zip_code = request.form["zip"]

        cur.execute("""
            INSERT INTO sites (customer_id, site_name, street, city, state, zip)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (customer_id, site_name, street, city, state, zip_code))

        conn.commit()
        flash("Site added successfully!", "success")
        return redirect(url_for("customers"))

    cur.execute("SELECT * FROM customers ORDER BY name ASC")
    customers = cur.fetchall()

    return render_template("add_site.html", customers=customers)


# -------------------------
# ADD JOB
# -------------------------
@app.route("/add_job", methods=["GET", "POST"])
def add_job():
    conn = get_db()
    cur = conn.cursor()

    if request.method == "POST":
        site_id = request.form["site_id"]
        job_type = request.form["job_type"]
        description = request.form["description"]
        date = request.form["date"]

        cur.execute("""
            INSERT INTO jobs (site_id, job_type, description, date)
            VALUES (?, ?, ?, ?)
        """, (site_id, job_type, description, date))

        conn.commit()
        flash("Job added successfully!", "success")
        return redirect(url_for("home"))

    cur.execute("SELECT * FROM sites ORDER BY site_name ASC")
    sites = cur.fetchall()

    return render_template("add_job.html", sites=sites)


# -------------------------
# EDIT SITE
# -------------------------
@app.route("/edit_site/<int:id>", methods=["GET", "POST"])
def edit_site(id):
    conn = get_db()
    cur = conn.cursor()

    if request.method == "POST":
        site_name = request.form["site_name"]
        street = request.form["street"]
        city = request.form["city"]
        state = request.form["state"]
        zip_code = request.form["zip"]

        cur.execute("""
            UPDATE sites
            SET site_name = ?, street = ?, city = ?, state = ?, zip = ?
            WHERE id = ?
        """, (site_name, street, city, state, zip_code, id))

        conn.commit()
        flash("Site updated successfully!", "success")
        return redirect(url_for("site_detail", id=id))

    cur.execute("SELECT * FROM sites WHERE id = ?", (id,))
    site = cur.fetchone()

    return render_template("edit_site.html", site=site)


# -------------------------
# EDIT JOB
# -------------------------
@app.route("/edit_job/<int:id>", methods=["GET", "POST"])
def edit_job(id):
    conn = get_db()
    cur = conn.cursor()

    if request.method == "POST":
        job_type = request.form["job_type"]
        description = request.form["description"]
        date = request.form["date"]

        cur.execute("""
            UPDATE jobs
            SET job_type = ?, description = ?, date = ?
            WHERE id = ?
        """, (job_type, description, date, id))

        conn.commit()
        flash("Job updated!", "success")
        return redirect(url_for("job_detail", id=id))

    cur.execute("SELECT * FROM jobs WHERE id = ?", (id,))
    job = cur.fetchone()

    return render_template("edit_job.html", job=job)


# -------------------------
# NEW CUSTOMER
# -------------------------
@app.route("/new_customer", methods=["GET", "POST"])
def new_customer():
    conn = get_db()
    cur = conn.cursor()

    if request.method == "POST":
        name = request.form["name"]
        phone = request.form["phone"]

        cur.execute("""
            INSERT INTO customers (name, phone)
            VALUES (?, ?)
        """, (name, phone))

        conn.commit()
        flash("Customer added!", "success")
        return redirect(url_for("customers"))

    return render_template("new_customer.html")


# -------------------------
# SETTINGS PAGE
# -------------------------
@app.route("/settings")
def settings_page():
    return render_template("settings.html")


# -------------------------
# CALENDAR VIEW  (IMPORTANT)
# -------------------------
@app.route("/calendar")
def calendar_view():
    return render_template("calendar.html")


# -------------------------
# Run App (local dev only)
# -------------------------
if __name__ == "__main__":
    app.run(debug=True)
