#!/usr/bin/env bash
set -o errexit

python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python manage.py check
python manage.py collectstatic --clear --noinput

# Use Neon's direct (non-pooled) connection for schema migrations.
# The running web service uses DATABASE_URL, which should be Neon's pooled URL.
if [ -n "${DIRECT_DATABASE_URL:-}" ]; then
  DATABASE_URL="${DIRECT_DATABASE_URL}" python manage.py migrate --noinput
else
  python manage.py migrate --noinput
fi
