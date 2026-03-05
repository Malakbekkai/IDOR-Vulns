# ◈ USER VAULT — Level 1 CTF Challenge

**Category:** Web
**Difficulty:** Easy
**Type:** Basic IDOR
**Flag:** `CTF{5equ3nt14l_1d5_4r3_n0t_4uth}`

---

## Description

A simple user profile system. Every user has a profile page. Can you read someone else's?

---

## Directory Structure

```
level1/
├── Dockerfile
├── app.py
├── database.db             ← auto-generated on first run
├── requirements.txt
├── static/
│   └── css/
│       └── style.css
└── templates/
    ├── login.html
    ├── register.html
    └── profile.html
```

---

## Quick Start

```bash
docker build -t level1 .
docker run -p 5001:5000 level1
```

Visit: `http://localhost:5001`

---

## How It Works

1. Users register and log in
2. After login they land on `/profile?id=<their_id>`
3. The `id` parameter is taken directly from the URL with **no ownership check**
4. The admin user (id=1) has the flag stored in their `bio` field

---

## Vulnerability

```python
# 🔴 VULNERABLE ROUTE
@app.route("/profile")
def profile():
    user_id = request.args.get("id")   # taken from URL directly
    user = conn.execute(
        "SELECT * FROM users WHERE id=?", (user_id,)
    ).fetchone()
    # ❌ never checks: user_id == session["user_id"]
    return render_template("profile.html", user=user)
```

---

## Solve — Step by Step

**Step 1** — Register an account and log in. Notice the URL:
```
/profile?id=2
```

**Step 2** — Change `id=2` to `id=1` in the URL:
```
/profile?id=1
```

**Step 3** — The admin's profile loads, bio field contains the flag:
```
CTF{5equ3nt14l_1d5_4r3_n0t_4uth}
```

---

## Intended Rabbit Holes

- None — this is level 1, the path is intentionally straightforward

---

## Customising the Flag

Edit `app.py` in `init_db()`:
```python
c.execute("""
    INSERT INTO users (username, password, bio)
    VALUES (?, ?, ?)
""", ("admin", "admin123", "YOUR_FLAG_HERE"))
```

---

## Notes for CTF Admins

- DB is **not** reset on restart — if you need a clean state, delete `database.db` and restart
- Admin credentials are `admin / admin123` — change `app.secret_key` before deploying
- Single Flask dev server — fine for small CTFs, swap for gunicorn if expecting high load