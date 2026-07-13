#!/bin/sh

# Worker only; beat runs separately (celery_beat_endpoint.sh) so the schedule
# fires once, not once per worker replica. Without an explicit --concurrency,
# prefork forks one process per node CPU regardless of the pod's CPU limit.
exec celery -A research_environment_api.worker worker --loglevel=info --concurrency="${CELERY_CONCURRENCY:-2}"
