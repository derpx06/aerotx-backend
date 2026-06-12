#!/usr/bin/env sh
set -eu

if [ "${SKIP_MIGRATIONS:-0}" != "1" ]; then
  alembic upgrade head
fi

case "${1:-api}" in
  api)
    exec uvicorn app.main:app --host 0.0.0.0 --port 8000
    ;;
  processing_worker)
    exec celery -A app.core.celery_app.celery_app worker -Q processing_queue -n processing_worker@%h --loglevel=INFO
    ;;
  llm_worker)
    exec celery -A app.core.celery_app.celery_app worker -Q llm_queue -n llm_worker@%h --loglevel=INFO
    ;;
  reporting_worker)
    exec celery -A app.core.celery_app.celery_app worker -Q reporting_queue -n reporting_worker@%h --loglevel=INFO
    ;;
  flower)
    exec celery -A app.core.celery_app.celery_app flower --port=5555
    ;;
  *)
    exec "$@"
    ;;
esac

