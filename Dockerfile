FROM python:3.12-slim AS builder
WORKDIR /build
COPY requirements.txt .
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt

FROM python:3.12-slim
RUN useradd --system --uid 10001 --no-create-home appuser \
    && mkdir /data && chown 10001 /data
WORKDIR /srv
COPY --from=builder /install /usr/local
COPY app ./app
ENV PYTHONUNBUFFERED=1 \
    DB_PATH=/data/shortener.db
USER 10001
EXPOSE 8000
CMD ["gunicorn", "--bind", "0.0.0.0:8000", "--workers", "1", "--threads", "4", "app.main:create_app()"]
