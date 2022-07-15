ARG TAG=python3.9-slim

FROM tiangolo/uvicorn-gunicorn-fastapi:$TAG

RUN apt-get update && apt-get install curl -y
RUN curl -sL https://deb.nodesource.com/setup_16.x | /bin/bash -
RUN apt-get install nodejs=16.* -y

RUN mkdir -p /var/run/celery
RUN mkdir -p /var/log/celery

WORKDIR /frontend
COPY ./frontend .
RUN npm ci

WORKDIR /app
COPY backend/requirements.txt .
RUN pip install -r requirements.txt
COPY ./backend/main.py .
COPY ./backend/app ./app

WORKDIR /frontend
RUN npm run build
RUN cp -r ./dist/* /app/

WORKDIR /app
