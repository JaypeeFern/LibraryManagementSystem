FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

COPY requirements.txt ./
RUN python -m pip install --no-cache-dir --requirement requirements.txt

COPY . .
COPY docker/entrypoint.sh /usr/local/bin/library-entrypoint
RUN chmod 0755 /usr/local/bin/library-entrypoint \
    && useradd --create-home --uid 10001 --no-log-init appuser \
    && mkdir -p /data/media \
    && chown -R appuser:appuser /app /data

ENV DATABASE_PATH=/data/db.sqlite3 \
    MEDIA_ROOT=/data/media \
    DJANGO_DEBUG=false

EXPOSE 8000

USER appuser

ENTRYPOINT ["/usr/local/bin/library-entrypoint"]
CMD ["gunicorn", "backend.wsgi:application", "--bind", "0.0.0.0:8000", "--workers", "3", "--access-logfile", "-", "--error-logfile", "-"]
