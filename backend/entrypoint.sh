#!/bin/sh
set -e

echo "Running Alembic migrations..."
cd /app/backend && alembic upgrade head

echo "Starting backend server..."
exec uvicorn backend.gateway.main:app --host 0.0.0.0 --port 8000 --reload --ws-max-size 1048576
