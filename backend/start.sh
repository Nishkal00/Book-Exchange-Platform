#!/bin/sh
# Container start for hosted deploys (Render free tier has no pre-deploy command):
# apply migrations, then serve on the platform-provided PORT (default 8000).
set -e
alembic upgrade head
exec uvicorn app.main:app --host 0.0.0.0 --port "${PORT:-8000}"
