FROM node:22-slim AS frontend-builder

WORKDIR /app/frontend

COPY frontend/package*.json ./
RUN if [ -f package-lock.json ]; then npm ci --no-audit --no-fund; else npm install --no-audit --no-fund; fi

COPY frontend/ ./
RUN mkdir -p /app/backend/static/frontend && npm run build

FROM python:3.12-slim AS application

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PORT=8000

WORKDIR /app/backend

COPY backend/requirements.txt ./requirements.txt
RUN python -m pip install --no-cache-dir --upgrade pip \
    && python -m pip install --no-cache-dir -r requirements.txt

COPY backend/ ./
COPY --from=frontend-builder /app/backend/static/frontend/ ./static/frontend/

RUN python biometrics/download_models.py \
    && DATABASE_URL=postgresql://rollnexa:build-only@127.0.0.1:5432/rollnexa \
        python manage.py check \
    && DATABASE_URL=postgresql://rollnexa:build-only@127.0.0.1:5432/rollnexa \
        python manage.py collectstatic --noinput \
    && addgroup --system rollnexa \
    && adduser --system --ingroup rollnexa rollnexa \
    && chown -R rollnexa:rollnexa /app/backend

USER rollnexa

EXPOSE 8000

CMD ["sh", "docker-entrypoint.sh"]
