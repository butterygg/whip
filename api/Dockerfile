ARG TAG=python3.9-slim

FROM tiangolo/uvicorn-gunicorn-fastapi:$TAG

COPY requirements.txt /app/

RUN pip install -r /app/requirements.txt

COPY ./app /app
