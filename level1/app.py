from flask import Flask, render_template, request, redirect, session
import sqlite3
import os

app = Flask(__name__)
app.secret_key = "supersecretkey"

DATABASE = "database.db"


def init_db():
    if not os.path.exists(DATABASE):
        conn = sqlite3.connect(DATABASE)
        c = conn.cursor()

        c.execute("""
            CREATE TABLE users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE,
                password TEXT,
                bio TEXT
            )
        """)

        # Admin user with flag
        c.execute("""
            INSERT INTO users (username, password, bio)
            VALUES (?, ?, ?)
        """, ("admin", "admin123", "FLAG{simple_idor_level1}"))

        conn.commit()
        conn.close()


def get_db():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn


@app.route("/")
def home():
    if "user_id" in session:
        return redirect(f"/profile?id={session['user_id']}")
    return redirect("/login")


@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]

        conn = get_db()
        try:
            conn.execute(
                "INSERT INTO users (username, password, bio) VALUES (?, ?, ?)",
                (username, password, "This is your profile bio.")
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
            return redirect(f"/profile?id={user['id']}")

        return "Invalid credentials"

    return render_template("login.html")


# 🔴 VULNERABLE ROUTE (IDOR HERE)
@app.route("/profile")
def profile():
    if "user_id" not in session:
        return redirect("/login")

    user_id = request.args.get("id")

    conn = get_db()
    user = conn.execute(
        "SELECT * FROM users WHERE id=?",
        (user_id,)
    ).fetchone()
    conn.close()

    if not user:
        return "User not found"

    # ❌ NO ownership verification
    return render_template("profile.html", user=user)


@app.route("/logout")
def logout():
    session.clear()
    return redirect("/login")


if __name__ == "__main__":
    init_db()
    app.run(host="0.0.0.0", port=5000)