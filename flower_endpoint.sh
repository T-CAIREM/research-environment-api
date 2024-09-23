#!/bin/sh

celery -A research_environment_api.worker flower

