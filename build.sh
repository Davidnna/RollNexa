#!/usr/bin/env sh
set -eu

ROOT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
cd "$ROOT_DIR"

npm --prefix frontend install --no-audit --no-fund
npm --prefix frontend run build

python -m pip install --upgrade pip
python -m pip install -r backend/requirements.txt

cd backend
python manage.py check
python manage.py collectstatic --clear --noinput

if [ -n "${DIRECT_DATABASE_URL:-}" ]; then
    DATABASE_URL="${DIRECT_DATABASE_URL}" python manage.py migrate --noinput
else
    python manage.py migrate --noinput
fi
