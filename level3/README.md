# ▣ THE ARCHIVE — CTF Challenge

**Category:** Web  
**Difficulty:** Medium 
**Type:** Chained IDOR (3 steps)  
**Flag:** `CTF{1D0R_ch41n_m4st3r_arc41v1st}`

---

## Directory Structure

```
the-archive/
├── Dockerfile
├── docker-compose.yml
├── README.md
└── app/
    ├── app.py                  # Flask application 
    ├── entrypoint.sh           # DB init + gunicorn start
    ├── requirements.txt
    ├── static/
    │   └── css/
    │       └── style.css
    └── templates/
        ├── base.html
        ├── login.html
        ├── register.html
        ├── dashboard.html
        ├── profile.html        # STEP 1: leaks numeric user ID in HTML comment
        ├── folder.html
        ├── new_doc.html
        └── admin_fake.html     # Dead-end 403 page
```

---

## Quick Start

```bash
# With Docker Compose (recommended)
docker compose up --build

# Or plain Docker
docker build -t the-archive .
docker run -p 5000:5000 -e FLAG="CTF{your_flag}" the-archive
```

Visit: http://localhost:5000

---

## Vulnerability Chain (Spoiler / Admin Reference)

### STEP 1 — Find the admin's internal numeric ID

Visit `/profile` after logging in. View the page source:

```html
<!-- system: render_uid=2 -->   ← your own ID
```

The admin's ID is always `1` (first user seeded). But players discover the
pattern by seeing their own ID in the comment and trying `1`.

---

### STEP 2 — Enumerate admin folders via unprotected `owner` param

`GET /folders` is supposed to return only your folders — but the `owner`
query parameter is **not** server-side validated against the session.

Response:
```json
[{"id": 1, "name": "Classified"}]
```

Admin's folder ID = **1**.

---

### STEP 3 — Export admin documents via IDOR on `/export`

`/export` checks that `folder` exists and that `doc` belongs to `folder` —
but **never checks folder.owner_id == current_user.id**.

Rate limit: 10 req/min per user.

Brute-force `doc` from 1 to ~10:


Doc ID **7** returns the flag:

```
=== TOP SECRET — DO NOT DISTRIBUTE ===

CTF{1D0R_ch41n_m4st3r_arc41v1st}
```

---

## Intended Rabbit Holes

- `/robots.txt` → `/api/v1/docs` (returns 401, dead end)
- `/admin` → 403 forbidden page
- UUID in profile page (the *public* identifier — not exploitable)

---
