FROM python:3.11-slim

RUN apt-get update -y && apt-get upgrade -y && apt-get install build-essential -y

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

CMD exec gunicorn --bind :$PORT --workers 1 --threads 8 --timeout 0 research_environment_api.wsgi:app
