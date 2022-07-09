# pylint: disable=invalid-name
import os

if "REDIS_TLS_URL" in os.environ:
    broker_url = os.environ["REDIS_TLS_URL"]
elif "REDIS_URL" in os.environ:
    broker_url = os.environ["REDIS_URL"]
else:
    broker_url = "redis://redis"

task_serializer = "json"
result_serializer = "json"
accept_content = ["json"]
timezone = "UTC"
enable_utc = True
