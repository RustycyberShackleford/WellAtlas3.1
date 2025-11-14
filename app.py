from flask import Flask, render_template, request, redirect, url_for, flash
import sqlite3
from datetime import datetime

app = Flask(__name__)
app.secret_key = "supersecretkey"

DATABASE = "wellatlas.db"

def get_db():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn

@app.route("/")
def home():
    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT * FROM customers ORDER BY name ASC")
    customers = cur.fetchall()
    return render_template("index.html", customers=customers)

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

@app.route("/site/<int:id>")
def site_detail(id):
    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT * FROM sites WHERE id = ?", (id,))
    site = cur.fetchone()

    cur.execute("SELECT * FROM jobs WHERE site_id = ?", (id,))
    jobs = cur.fetchall()

    return render_template("site_detail.html", site=site, jobs=jobs)

@app.route("/job/<int:id>")
def job_detail(id):
    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT * FROM jobs WHERE id = ?", (id,))
    job = cur.fetchone()
    return render_template("job_detail.html", job=job)

@app.route("/settings")
def settings():
    return render_template("settings.html")

@app.errorhandler(404)
def not_found(e):
    return "Page not found", 404
