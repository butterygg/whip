FROM python:3.9.12-buster

RUN mkdir -p /var/run/celery
RUN mkdir -p /var/log/celery

COPY requirements.txt /app/

RUN pip install -r /app/requirements.txt
