# Optional Phase 1 scaffold; Docker build/runtime has NOT been verified.
FROM node:24-alpine AS frontend
WORKDIR /build/frontend
COPY frontend/package*.json ./
RUN npm ci --no-audit --no-fund
COPY frontend/ ./
RUN npm run build

FROM python:3.12-slim
WORKDIR /app
COPY backend/requirements.txt /app/backend/requirements.txt
RUN pip install --no-cache-dir -r backend/requirements.txt \
    && useradd --create-home --uid 10001 compass \
    && mkdir /data && chown compass:compass /data
COPY backend/app /app/backend/app
COPY data/seed_manifest.json /app/data/seed_manifest.json
COPY --from=frontend /build/frontend/dist /app/frontend/dist
ENV PYTHONPATH=/app/backend AP_COMPASS_DB_PATH=/data/ap-compass.db PYTHONUNBUFFERED=1
USER compass
EXPOSE 8000
CMD ["sh", "-c", "exec uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
