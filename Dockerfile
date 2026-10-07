# EdgeHealth web image: API + built interface served by Waitress on port 8000.
# The SQLite database lives in the /data volume, which must be persistent.
FROM node:22-alpine AS frontend
WORKDIR /src/frontend
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build

FROM python:3.12-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 \
    DATABASE_URL=sqlite:////data/edgehealth.db \
    COOKIE_SECURE=true \
    TRUST_PROXY=1
WORKDIR /app/backend
COPY backend/requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt
COPY backend/ ./
COPY --from=frontend /src/frontend/dist /app/frontend/dist
RUN useradd --system --uid 10001 --home /app edgehealth \
    && mkdir -p /data /app/backend/instance \
    && chown -R edgehealth /data /app/backend/instance
USER edgehealth
VOLUME ["/data"]
EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=5s --start-period=20s \
  CMD python -c "import urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:8000/api/health',timeout=4).status==200 else 1)"
ENTRYPOINT ["sh", "/app/backend/docker-entrypoint.sh"]
CMD ["web"]
