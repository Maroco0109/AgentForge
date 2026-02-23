#!/bin/sh
set -e

echo "Running Alembic migrations..."
cd /app/backend && alembic upgrade head

echo "Starting backend server..."
if [ "${DEBUG:-false}" = "true" ]; then
    exec uvicorn backend.gateway.main:app --host 0.0.0.0 --port 8000 --reload --ws-max-size 1048576
else
    exec uvicorn backend.gateway.main:app --host 0.0.0.0 --port 8000 --workers 4 --ws-max-size 1048576
fi
