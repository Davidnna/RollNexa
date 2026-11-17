#!/bin/sh
set -eu

if [ -n "${DIRECT_DATABASE_URL:-}" ]; then
    DATABASE_URL="${DIRECT_DATABASE_URL}" python manage.py migrate --noinput
else
    python manage.py migrate --noinput
fi

exec gunicorn config.wsgi:application \
    --bind "0.0.0.0:${PORT:-8000}" \
    --workers "${WEB_CONCURRENCY:-1}" \
    --threads 4 \
    --timeout 120
