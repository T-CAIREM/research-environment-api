#!/bin/sh
# this is load-test only script, do not use it in other environments

apt-get update -y
apt-get install postgresql-client -y

HOST=$(echo "${RESEARCH_ENV_API_CLOUD_SQL_PORT}" | sed 's/tcp:\/\///' | cut -d':' -f1)

PGPASSWORD="postgres" psql -h "$HOST" -U "postgres" -d "dev" -c \
'GRANT ALL ON SCHEMA public TO "billing-account-manager@research-env-api-load-test.iam";'
