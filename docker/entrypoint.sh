#!/bin/sh
set -eu

mkdir -p "$(dirname "$DATABASE_PATH")" "$MEDIA_ROOT"
python manage.py migrate --noinput
python manage.py collectstatic --noinput

exec "$@"
