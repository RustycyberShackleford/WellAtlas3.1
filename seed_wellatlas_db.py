# seed_wellatlas_db.py
import os
import sqlite3
import random
from datetime import date, timedelta

DB_PATH = os.path.join(os.path.dirname(__file__), "wellatlas_v4_demo.db")

def main():
    if os.path.exists(DB_PATH):
        os.remove(DB_PATH)

    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    # Tables (match your init_db in app.py)
    c.execute("""
    CREATE TABLE customers (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        notes TEXT
    )
    """)

    c.execute("""
    CREATE TABLE sites (
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

    c.execute("""
    CREATE TABLE jobs (
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

    c.execute("""
    CREATE TABLE job_files (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        job_id INTEGER NOT NULL,
        filename TEXT NOT NULL,
        filetype TEXT NOT NULL,
        url TEXT NOT NULL
    )
    """)

    c.execute("""
    CREATE TABLE job_notes (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        job_id INTEGER NOT NULL,
        text TEXT NOT NULL,
        timestamp TEXT NOT NULL
    )
    """)

    conn.commit()

    # 40 presidents
    presidents = [
        "George Washington", "John Adams", "Thomas Jefferson", "James Madison",
        "James Monroe", "John Quincy Adams", "Andrew Jackson", "Martin Van Buren",
        "William Henry Harrison", "John Tyler", "James K. Polk", "Zachary Taylor",
        "Millard Fillmore", "Franklin Pierce", "James Buchanan", "Abraham Lincoln",
        "Andrew Johnson", "Ulysses S. Grant", "Rutherford B. Hayes", "James A. Garfield",
        "Chester A. Arthur", "Grover Cleveland (1st)", "Benjamin Harrison", "Grover Cleveland (2nd)",
        "William McKinley", "Theodore Roosevelt", "William Howard Taft", "Woodrow Wilson",
        "Warren G. Harding", "Calvin Coolidge", "Herbert Hoover", "Franklin D. Roosevelt",
        "Harry S. Truman", "Dwight D. Eisenhower", "John F. Kennedy", "Lyndon B. Johnson",
        "Richard Nixon", "Gerald Ford", "Jimmy Carter", "Ronald Reagan"
    ]

    for name in presidents:
        c.execute("INSERT INTO customers (name, notes) VALUES (?, ?)", (name, ""))

    # Region centers: Chico, Willows, Durham, Corning, Red Bluff, Cottonwood
    centers = [
        (39.7285, -121.8375),  # Chico
        (39.5243, -122.1937),  # Willows
        (39.6402, -121.8003),  # Durham
        (39.9270, -122.1817),  # Corning
        (40.1785, -122.2358),  # Red Bluff
        (40.3843, -122.2800),  # Cottonwood
    ]

    def jitter(lat, lng):
        return lat + random.uniform(-0.05, 0.05), lng + random.uniform(-0.05, 0.05)

    # 20 sites per customer → 800 sites
    site_ids = []
    for cust_id in range(1, 41):
        for i in range(20):
            base_lat, base_lng = random.choice(centers)
            lat, lng = jitter(base_lat, base_lng)
            site_name = f"Site {cust_id}-{i+1}"
            c.execute("""
                INSERT INTO sites (customer_id, site_name, street, city, state, zip,
                                   contact_name, phone, email, notes, lat, lng)
                VALUES (?, ?, '', '', '', '', '', '', '', '', ?, ?)
            """, (cust_id, site_name, lat, lng))
            site_ids.append(c.lastrowid)

    # Jobs: global never-reset per division
    divisions = ["D", "A", "P", "E"]
    division_names = {"D": "Drilling", "A": "Ag", "P": "Domestic", "E": "Electrical"}
    statuses = ["Scheduled", "In Progress", "Completed", "On Hold"]
    seq = {"D": 1, "A": 1, "P": 1, "E": 1}

    def random_dates():
        start_base = date(2023, 1, 1)
        offset = random.randint(0, 365 * 2)  # ~2-year spread
        start = start_base + timedelta(days=offset)
        dur = random.randint(1, 14)
        end = start + timedelta(days=dur)
        return start, end

    for site_id in site_ids:
        num_jobs = random.randint(10, 20)
        for _ in range(num_jobs):
            div = random.choice(divisions)
            n = seq[div]
            seq[div] += 1
            job_number = f"{div}25{n:03d}"
            title = f"{division_names[div]} Job {job_number}"
            status = random.choice(statuses)
            desc = f"{division_names[div]} job {job_number} at site {site_id}"
            sd, ed = random_dates()
            c.execute("""
                INSERT INTO jobs (site_id, job_number, title, division, status, description, start_date, end_date)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (site_id, job_number, title, division_names[div], status, desc,
                  sd.isoformat(), ed.isoformat()))

    conn.commit()
    conn.close()
    print("Seeded wellatlas_v4_demo.db successfully.")

if __name__ == "__main__":
    main()
