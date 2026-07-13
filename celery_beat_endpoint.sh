#!/bin/sh

# Schedule publisher — must run as a singleton (one replica) or scheduled
# tasks are duplicated.
exec celery -A research_environment_api.worker beat --loglevel=info
