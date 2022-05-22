ARG TAG=python3.9-slim

FROM tiangolo/uvicorn-gunicorn-fastapi:$TAG

RUN mkdir -p /var/run/celery
RUN mkdir -p /var/log/celery
RUN mkdir -p /app/

COPY requirements.txt /app/

RUN pip install -r /app/requirements.txt

COPY ./app /app/app

WORKDIR /app