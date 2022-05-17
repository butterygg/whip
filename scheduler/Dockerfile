FROM python:3.9.7-buster

RUN mkdir -p /var/run/celery
RUN mkdir -p /var/log/celery
RUN mkdir -p /entrypoint/app

WORKDIR /entrypoint

COPY requirements.txt /app/

RUN pip install -r /app/requirements.txt

COPY ./app /app

RUN python -c "import app"

RUN touch __init__.py

# CMD [ "celery", "-A", "celery", "worker", "-l", "DEBUG", "--pidfile=/var/run/celery/%n.pid", "--logfile=/var/log/celery/%n%I.log" ]
