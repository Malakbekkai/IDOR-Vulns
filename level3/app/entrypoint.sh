#!/bin/sh
set -e

echo "[*] Initializing database..."
python -c "from app import init_db; init_db()"

echo "[*] Starting The Archive..."
exec gunicorn \
  --bind 0.0.0.0:5000 \
  --workers 4 \
  --timeout 30 \
  --access-logfile - \
  --error-logfile - \
  app:app
