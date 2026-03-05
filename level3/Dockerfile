FROM python:3.12-slim

LABEL challenge="the-archive"
LABEL difficulty="hard"
LABEL category="web/idor"

# Non-root user for safety
RUN useradd -m -s /bin/bash appuser

WORKDIR /app

# Install dependencies
COPY app/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy app
COPY app/ .

# Make entrypoint executable
RUN chmod +x entrypoint.sh

# DB lives in /tmp — writable, ephemeral per container, no volume needed
ENV DATABASE=/tmp/archive.db
ENV SECRET_KEY=ctf_secret_key_change_for_prod
ENV FLAG=CTF{1D0R_ch41n_m4st3r_arc41v1st}

# Switch to non-root
USER appuser

EXPOSE 5000

ENTRYPOINT ["./entrypoint.sh"]
