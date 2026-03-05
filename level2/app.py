from flask import Flask, render_template, request, redirect, session
import sqlite3
import os

app = Flask(__name__)
app.secret_key = "level2secret"

DATABASE = "database.db"


def init_db():
    # Reset DB every container restart (good for CTF)
    if os.path.exists(DATABASE):
        os.remove(DATABASE)

    conn = sqlite3.connect(DATABASE)
    c = conn.cursor()

    # Users table
    c.execute("""
        CREATE TABLE users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE,
            password TEXT
        )
    """)

    # Documents table
    c.execute("""
        CREATE TABLE documents (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            owner_id INTEGER,
            title TEXT,
            content TEXT,
            public_id TEXT UNIQUE
        )
    """)

    # Create admin user
    c.execute("INSERT INTO users (username, password) VALUES (?, ?)",
              ("admin", "admin123"))

    # Insert noise invoices INV-0001 → INV-0008
    for i in range(1, 9):
        public_id = f"INV-{i:03d}"
        c.execute("""
            INSERT INTO documents (owner_id, title, content, public_id)
            VALUES (?, ?, ?, ?)
        """, (
            1,
            f"Financial Report {i}",
            f"Internal accounting data for report {i}",
            public_id
        ))

    # 🔥 FLAG at INV-0009
    c.execute("""
        INSERT INTO documents (owner_id, title, content, public_id)
        VALUES (?, ?, ?, ?)
    """, (
        1,
        "Executive Financial Summary",
        "FLAG{medium_idor_invoice_009}",
        "INV-009"
    ))

    conn.commit()
    conn.close()


def get_db():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn


@app.route("/")
def home():
    if "user_id" in session:
        return redirect("/dashboard")
    return redirect("/login")


@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]

        conn = get_db()
        try:
            conn.execute(
                "INSERT INTO users (username, password) VALUES (?, ?)",
                (username, password)
            )
            conn.commit()
        except:
            return "Username already exists"
        finally:
            conn.close()

        return redirect("/login")

    return render_template("register.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]

        conn = get_db()
        user = conn.execute(
            "SELECT * FROM users WHERE username=? AND password=?",
            (username, password)
        ).fetchone()
        conn.close()

        if user:
            session["user_id"] = user["id"]
            return redirect("/dashboard")

        return "Invalid credentials"

    return render_template("login.html")


@app.route("/dashboard")
def dashboard():
    if "user_id" not in session:
        return redirect("/login")

    conn = get_db()
    docs = conn.execute(
        "SELECT public_id, title FROM documents WHERE owner_id=?",
        (session["user_id"],)
    ).fetchall()
    conn.close()

    return render_template("dashboard.html", docs=docs)


# 🔴 VULNERABLE ROUTE (PURE IDOR)
@app.route("/invoice/<public_id>")
def invoice(public_id):
    if "user_id" not in session:
        return redirect("/login")

    conn = get_db()
    doc = conn.execute(
        "SELECT * FROM documents WHERE public_id=?",
        (public_id,)
    ).fetchone()
    conn.close()

    if not doc:
        return "Invoice not found"

    # ❌ NO ownership validation
    return render_template("invoice.html", doc=doc)


@app.route("/logout")
def logout():
    session.clear()
    return redirect("/login")


if __name__ == "__main__":
    init_db()
    app.run(host="0.0.0.0", port=5000)