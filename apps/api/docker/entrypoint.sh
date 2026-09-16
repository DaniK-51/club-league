#!/bin/sh
set -e

echo "Applying Alembic migrations..."
alembic upgrade head

if [ "${SEED_DEV_USERS:-false}" = "true" ]; then
  echo "Seeding dev users..."
  python -m scripts.seed_dev_users
fi

echo "Starting API..."
exec "$@"
