FROM tiangolo/uvicorn-gunicorn-fastapi:python3.9-slim

COPY requirements.txt /app/

RUN pip install -r /app/requirements.txt

COPY ./app /app
