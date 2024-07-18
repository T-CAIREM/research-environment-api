#!/bin/sh

python -m http.server 8080 &

celery -A research_environment_api.worker worker --loglevel=info &
celery -A research_environment_api.worker beat --loglevel=info &

&& fg
