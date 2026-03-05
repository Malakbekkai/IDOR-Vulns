import os
import sqlite3
import uuid
import hashlib
import time
from functools import wraps
from flask import (
    Flask, request, session, redirect, url_for,
    render_template, jsonify, g, abort, send_file
)
from io import BytesIO
import threading

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "dev-secret-change-in-prod")

DATABASE = "/tmp/archive.db"
RATE_LIMIT = {}
RATE_LIMIT_LOCK = threading.Lock()



def get_db():
    db = getattr(g, "_database", None)
    if db is None:
        db = g._database = sqlite3.connect(DATABASE)
        db.row_factory = sqlite3.Row
    return db

@app.teardown_appcontext
def close_connection(exception):
    db = getattr(g, "_database", None)
    if db is not None:
        db.close()

def init_db():
    db = sqlite3.connect(DATABASE)
    db.row_factory = sqlite3.Row
    c = db.cursor()

    c.executescript("""
        CREATE TABLE IF NOT EXISTS users (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            uuid        TEXT UNIQUE NOT NULL,
            username    TEXT UNIQUE NOT NULL,
            password    TEXT NOT NULL,
            is_admin    INTEGER DEFAULT 0
        );

        CREATE TABLE IF NOT EXISTS folders (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            owner_id    INTEGER NOT NULL,
            name        TEXT NOT NULL,
            FOREIGN KEY(owner_id) REFERENCES users(id)
        );

        CREATE TABLE IF NOT EXISTS documents (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            folder_id   INTEGER NOT NULL,
            owner_id    INTEGER NOT NULL,
            title       TEXT NOT NULL,
            content     TEXT NOT NULL,
            is_secret   INTEGER DEFAULT 0,
            FOREIGN KEY(folder_id) REFERENCES folders(id),
            FOREIGN KEY(owner_id)  REFERENCES users(id)
        );
    """)

    
    admin = db.execute("SELECT id FROM users WHERE username='admin'").fetchone()
    if not admin:
        admin_uuid = str(uuid.uuid4())
        admin_pass = hashlib.sha256(b"sup3r_s3cr3t_adm1n").hexdigest()
        c.execute(
            "INSERT INTO users (uuid, username, password, is_admin) VALUES (?,?,?,1)",
            (admin_uuid, "admin", admin_pass)
        )
        db.commit()
        admin = db.execute("SELECT id FROM users WHERE username='admin'").fetchone()
        admin_id = admin["id"]

        # Admin folder (id will be low, e.g. 1)
        c.execute(
            "INSERT INTO folders (owner_id, name) VALUES (?,?)",
            (admin_id, "Classified")
        )
        db.commit()
        folder = db.execute(
            "SELECT id FROM folders WHERE owner_id=? AND name='Classified'", (admin_id,)
        ).fetchone()
        folder_id = folder["id"]

        
        decoys = [
            "Q3 financial projections — see attached sheet.",
            "HR onboarding checklist for new employees.",
            "Server maintenance window: Saturday 02:00–04:00 UTC.",
            "Marketing campaign brief for product launch.",
            "Legal review notes — NDA template v2.",
            "Board meeting minutes — redacted copy.",
        ]
        for title_body in decoys:
            c.execute(
                "INSERT INTO documents (folder_id, owner_id, title, content, is_secret) VALUES (?,?,?,?,0)",
                (folder_id, admin_id, title_body[:30], title_body)
            )

        # THE FLAG (doc id 7)
        flag = os.environ.get("FLAG", "CTF{1D0R_ch41n_m4st3r_arc41v1st}")
        c.execute(
            "INSERT INTO documents (folder_id, owner_id, title, content, is_secret) VALUES (?,?,?,?,1)",
            (folder_id, admin_id, "TOP SECRET — DO NOT DISTRIBUTE", flag)
        )
        db.commit()

    db.close()



def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if "user_id" not in session:
            return redirect(url_for("login"))
        
        user = get_db().execute(
            "SELECT id FROM users WHERE id=?", (session["user_id"],)
        ).fetchone()
        if user is None:
            session.clear()
            return redirect(url_for("login"))
        return f(*args, **kwargs)
    return decorated

def current_user():
    if "user_id" not in session:
        return None
    return get_db().execute(
        "SELECT * FROM users WHERE id=?", (session["user_id"],)
    ).fetchone()



def rate_limit_check(key, max_per_minute=12):
    now = time.time()
    with RATE_LIMIT_LOCK:
        hits = RATE_LIMIT.get(key, [])
        hits = [t for t in hits if now - t < 60]
        if len(hits) >= max_per_minute:
            return False
        hits.append(now)
        RATE_LIMIT[key] = hits
    return True



@app.route("/")
def index():
    if "user_id" in session:
        return redirect(url_for("dashboard"))
    return redirect(url_for("login"))

@app.route("/register", methods=["GET", "POST"])
def register():
    error = None
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "").strip()
        if not username or not password:
            error = "All fields required."
        elif len(username) < 3 or len(username) > 20:
            error = "Username must be 3–20 characters."
        else:
            db = get_db()
            existing = db.execute(
                "SELECT id FROM users WHERE username=?", (username,)
            ).fetchone()
            if existing:
                error = "Username already taken."
            else:
                uid = str(uuid.uuid4())
                pw  = hashlib.sha256(password.encode()).hexdigest()
                db.execute(
                    "INSERT INTO users (uuid, username, password) VALUES (?,?,?)",
                    (uid, username, pw)
                )
                db.commit()
                user = db.execute(
                    "SELECT * FROM users WHERE username=?", (username,)
                ).fetchone()
                # Create a default folder for the user
                db.execute(
                    "INSERT INTO folders (owner_id, name) VALUES (?,?)",
                    (user["id"], "My Documents")
                )
                db.commit()
                session["user_id"] = user["id"]
                return redirect(url_for("dashboard"))
    return render_template("register.html", error=error)

@app.route("/login", methods=["GET", "POST"])
def login():
    error = None
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "").strip()
        pw_hash  = hashlib.sha256(password.encode()).hexdigest()
        db = get_db()
        user = db.execute(
            "SELECT * FROM users WHERE username=? AND password=?",
            (username, pw_hash)
        ).fetchone()
        if not user:
            error = "Invalid credentials."
        else:
            session["user_id"] = user["id"]
            return redirect(url_for("dashboard"))
    return render_template("login.html", error=error)

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))

@app.route("/dashboard")
@login_required
def dashboard():
    user = current_user()
    db   = get_db()
    folders = db.execute(
        "SELECT * FROM folders WHERE owner_id=?", (user["id"],)
    ).fetchall()
    
    folder_data = []
    for f in folders:
        count = db.execute(
            "SELECT COUNT(*) as cnt FROM documents WHERE folder_id=? AND owner_id=?",
            (f["id"], user["id"])
        ).fetchone()["cnt"]
        folder_data.append({"id": f["id"], "name": f["name"], "doc_count": count})
    return render_template("dashboard.html", user=user, folders=folder_data)

@app.route("/profile")
@login_required
def profile():
    user = current_user()
    
    return render_template("profile.html", user=user)


@app.route("/folders")
@login_required
def list_folders():
    # 'owner' param should be session-locked — but it's not ¯\_(ツ)_/¯
    owner_id = request.args.get("owner", session.get("user_id"))
    try:
        owner_id = int(owner_id)
    except (TypeError, ValueError):
        abort(400)

    db = get_db()
    folders = db.execute(
        "SELECT id, name FROM folders WHERE owner_id=?", (owner_id,)
    ).fetchall()
    return jsonify([{"id": f["id"], "name": f["name"]} for f in folders])

@app.route("/folder/<int:folder_id>")
@login_required
def view_folder(folder_id):
    user = current_user()
    db   = get_db()
    folder = db.execute("SELECT * FROM folders WHERE id=?", (folder_id,)).fetchone()
    if not folder:
        abort(404)
    # Only owner can VIEW folder page
    if folder["owner_id"] != user["id"]:
        abort(403)
    docs = db.execute(
        "SELECT id, title FROM documents WHERE folder_id=? AND owner_id=?",
        (folder_id, user["id"])
    ).fetchall()
    return render_template("folder.html", user=user, folder=folder, docs=docs)

@app.route("/document/new", methods=["GET", "POST"])
@login_required
def new_document():
    user = current_user()
    db   = get_db()
    if request.method == "POST":
        folder_id = request.form.get("folder_id")
        title     = request.form.get("title", "").strip()
        content   = request.form.get("content", "").strip()
        if not folder_id or not title or not content:
            return render_template("new_doc.html", user=user,
                                   folders=db.execute("SELECT * FROM folders WHERE owner_id=?",
                                                      (user["id"],)).fetchall(),
                                   error="All fields required.")
        folder = db.execute(
            "SELECT * FROM folders WHERE id=? AND owner_id=?",
            (folder_id, user["id"])
        ).fetchone()
        if not folder:
            abort(403)
        db.execute(
            "INSERT INTO documents (folder_id, owner_id, title, content) VALUES (?,?,?,?)",
            (folder_id, user["id"], title, content)
        )
        db.commit()
        return redirect(url_for("view_folder", folder_id=folder_id))
    folders = db.execute(
        "SELECT * FROM folders WHERE owner_id=?", (user["id"],)
    ).fetchall()
    return render_template("new_doc.html", user=user, folders=folders, error=None)


@app.route("/export")
@login_required
def export_document():
    user      = current_user()
    folder_id = request.args.get("folder")
    doc_id    = request.args.get("doc")
    fmt       = request.args.get("format", "txt")

    if not folder_id or not doc_id:
        abort(400)

    
    if not rate_limit_check(f"export:{user['id']}", max_per_minute=12):
        return jsonify({"error": "Rate limit exceeded. Try again in a minute."}), 429

    try:
        folder_id = int(folder_id)
        doc_id    = int(doc_id)
    except ValueError:
        abort(400)

    db = get_db()

    # checks folder exists + doc matches folder,
    # but NEVER checks folder.owner_id == user.id
    folder = db.execute("SELECT * FROM folders WHERE id=?", (folder_id,)).fetchone()
    if not folder:
        abort(404)

    doc = db.execute(
        "SELECT * FROM documents WHERE id=? AND folder_id=?",
        (doc_id, folder_id)
    ).fetchone()
    if not doc:
        abort(404)

    content = doc["content"]
    title   = doc["title"]

    if fmt == "txt":
        buf = BytesIO(f"=== {title} ===\n\n{content}\n".encode())
        return send_file(buf, mimetype="text/plain",
                         download_name=f"doc_{doc_id}.txt", as_attachment=True)
    else:
        # Simple "PDF-like" plaintext wrapped
        body = f"DOCUMENT EXPORT\n{'='*40}\nTitle: {title}\n{'='*40}\n\n{content}\n"
        buf  = BytesIO(body.encode())
        return send_file(buf, mimetype="application/octet-stream",
                         download_name=f"doc_{doc_id}.pdf", as_attachment=True)


@app.route("/robots.txt")
def robots():
    return app.response_class(
        "User-agent: *\nDisallow: /api/v1/docs\nDisallow: /admin\n",
        mimetype="text/plain"
    )

# ── Dead end API ──
@app.route("/api/v1/docs")
def fake_api():
    return jsonify({"error": "Unauthorized", "hint": "Wrong path, keep looking."}), 401

@app.route("/admin")
def fake_admin():
    return render_template("admin_fake.html"), 403

if __name__ == "__main__":
    init_db()
    app.run(host="0.0.0.0", port=5000, debug=False)
