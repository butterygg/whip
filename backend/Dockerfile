ARG TAG=python3.9-slim

FROM tiangolo/uvicorn-gunicorn-fastapi:$TAG

RUN mkdir -p /var/run/celery
RUN mkdir -p /var/log/celery

WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY ./main.py .
COPY ./app ./app
